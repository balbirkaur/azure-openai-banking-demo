import { useState } from "react";

type Role = "user" | "bot";

interface Message {
  from: Role;
  text: string;
}

export function ChatBot() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  // Stored once user is authenticated
  const [accountNumber, setAccountNumber] = useState<string | null>(null);
  const [pin, setPin] = useState<string | null>(null);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userText = input.trim();

    setMessages((prev) => [...prev, { from: "user", text: userText }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          account_number: accountNumber,
          pin,
        }),
      });

      const data = await res.json();
      const reply: string = data.error || data.reply || "Something went wrong.";
      const lowerReply = reply.toLowerCase();

    if (!accountNumber && lowerReply.includes("account found")) {
  setAccountNumber(userText);
}

if (accountNumber && !pin && lowerReply.includes("pin verified")) {
  setPin(userText);
}


      setMessages((prev) => [...prev, { from: "bot", text: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { from: "bot", text: "Server error. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") sendMessage();
  };
const getPlaceholder = () => {
  if (!accountNumber) return "Enter your account number";
  if (!pin) return "Enter PIN";
  return "Type your banking request";
};

  return (
  <div className="h-screen flex items-center justify-center bg-slate-900 text-slate-100 overflow-hidden">
    <div className="w-full max-w-xl h-[90vh] bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-50">
            ABC Bank – AI Assistant
          </h1>
          <p className="text-xs text-slate-400">
            Type hi to start. System will ask for account number and PIN.
          </p>
        </div>
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-emerald-900 text-emerald-300 text-sm font-bold">
          🤖
        </span>
      </div>

      {/* Messages */}
      <div className="px-4 py-3 flex-1 min-h-0 overflow-y-auto bg-slate-900">
        {messages.length === 0 && (
          <p className="text-xs text-slate-500 text-center mt-8">
            Type <span className="font-semibold text-slate-200">"hi"</span> to
            begin.
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`my-1 flex ${
              m.from === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-3 py-1.5 text-sm ${
                m.from === "user"
                  ? "bg-emerald-600 text-white rounded-br-sm"
                  : "bg-slate-800 border border-slate-600 text-slate-100 rounded-bl-sm"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="mt-2 text-xs text-slate-400">
            Bot is thinking<span className="animate-pulse">...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-slate-800 bg-slate-900 flex gap-2">
        <input
  className="flex-1 rounded-full border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
  placeholder={getPlaceholder()}
  value={input}
  onChange={(e) => setInput(e.target.value)}
  onKeyDown={handleKey}
/>

        <button
          onClick={sendMessage}
          disabled={loading}
          className="inline-flex items-center justify-center rounded-full bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-60"
        >
          Send
        </button>
      </div>
    </div>
  </div>
);

}
