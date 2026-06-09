const messages = document.querySelector("#messages");
const form = document.querySelector("#composer");
const input = document.querySelector("#input");
const statusEl = document.querySelector("#status");

const history = [];

function addMessage(role, content, sources = []) {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = content;
  if (sources.length) {
    const sourceEl = document.createElement("div");
    sourceEl.className = "sources";
    sourceEl.textContent = `Sources: ${sources.map((s) => s.title).join(", ")}`;
    el.appendChild(sourceEl);
  }
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

addMessage(
  "assistant",
  "Hi, I am Kuldeep's AI representative. Ask me about his background, GitHub projects, fit for the role, or availability. I will stay grounded in the resume and repository evidence I can retrieve."
);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addMessage("user", text);
  history.push({ role: "user", content: text });
  statusEl.textContent = "Thinking";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ messages: history })
    });
    const data = await response.json();
    history.push({ role: "assistant", content: data.answer });
    addMessage("assistant", data.answer, data.sources || []);
  } catch (error) {
    addMessage("assistant", "I could not reach the chat service. Please try again in a moment.");
  } finally {
    statusEl.textContent = "Grounded";
  }
});

document.querySelector("#bookButton").addEventListener("click", async () => {
  const button = document.querySelector("#bookButton");
  const result = document.querySelector("#bookingResult");
  button.disabled = true;
  result.textContent = "Checking calendar...";

  try {
    const payload = {
      name: document.querySelector("#bookName").value,
      email: document.querySelector("#bookEmail").value,
      start: document.querySelector("#bookStart").value,
      source: "chat-ui"
    };
    const response = await fetch("/api/book", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    result.textContent = data.message || data.error || "Booking request completed.";
  } catch (error) {
    result.textContent = "The booking service is unavailable right now.";
  } finally {
    button.disabled = false;
  }
});
