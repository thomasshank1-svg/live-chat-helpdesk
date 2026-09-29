let state = { conversations: [], messages: [], canned: [], statuses: [] };
let activeId = null;

function renderConversations() {
  $("#count").textContent = `${state.conversations.length} chats`;
  if (!activeId && state.conversations[0]) activeId = state.conversations[0].id;
  $("#conversations").innerHTML = state.conversations.map((chat) => `
    <article class="item conversation ${chat.id === activeId ? "active" : ""}" data-open="${chat.id}">
      <div><h3>${esc(chat.topic)}</h3><p>${esc(chat.visitor)}<br><span class="muted">${new Date(chat.created_at).toLocaleString()}</span></p></div>
      <select data-status="${chat.id}">${state.statuses.map((s) => `<option ${s === chat.status ? "selected" : ""}>${esc(s)}</option>`).join("")}</select>
    </article>
  `).join("");
  document.querySelectorAll("[data-open]").forEach((card) => card.addEventListener("click", async (event) => {
    if (event.target.tagName === "SELECT") return;
    activeId = Number(card.dataset.open);
    const result = await api("/api/messages-for", { conversation_id: activeId });
    state.messages = result.messages;
    renderConversations();
    renderMessages();
  }));
  document.querySelectorAll("[data-status]").forEach((select) => select.addEventListener("change", () => action(select, async () => {
    await api("/api/status", { id: Number(select.dataset.status), status: select.value });
    await refresh();
  })));
}

function renderMessages() {
  $("#messages").innerHTML = state.messages.map((message) => `
    <div class="bubble ${message.author}"><strong>${esc(message.author)}</strong><p>${esc(message.body)}</p></div>
  `).join("") || '<p class="muted">Select a conversation.</p>';
}

async function refresh() {
  state = await api("/api/state");
  if (!activeId && state.conversations[0]) activeId = state.conversations[0].id;
  if (activeId) state.messages = (await api("/api/messages-for", { conversation_id: activeId })).messages;
  $("#canned").innerHTML = '<option value="">Canned replies</option>' + state.canned.map((text) => `<option>${esc(text)}</option>`).join("");
  renderConversations();
  renderMessages();
}

$("#canned").addEventListener("change", (event) => { if (event.target.value) $("#replyForm textarea").value = event.target.value; });
$("#replyForm").addEventListener("submit", (event) => {
  event.preventDefault();
  action(event.submitter, async () => {
    if (!activeId) throw new Error("Select a conversation first.");
    await api("/api/messages", { conversation_id: activeId, author: "agent", body: new FormData(event.currentTarget).get("body") });
    event.currentTarget.reset();
    await refresh();
  });
});
$("#newForm").addEventListener("submit", (event) => {
  event.preventDefault();
  action(event.submitter, async () => {
    const result = await api("/api/conversations", Object.fromEntries(new FormData(event.currentTarget)));
    activeId = result.id;
    event.currentTarget.reset();
    await refresh();
    toast("Chat started.");
  });
});
refresh().catch((error) => toast(error.message));
