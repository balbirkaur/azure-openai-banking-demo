import { useEffect, useRef, useState } from "react";

type Role = "user" | "bot";

interface Message {
  from: Role;
  text: string;
  time: string;
}

export function ChatBot() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const [accountNumber, setAccountNumber] = useState<string>("");
  const [pin, setPin] = useState<string>("");
  const [isVerified, setIsVerified] = useState(false);

  const [userName, setUserName] = useState<string>("");
  const [balance, setBalance] = useState<number | null>(null);

  const [activeTab, setActiveTab] = useState<
    "Balance" | "Deposit" | "Withdraw" | "Transfer" | "Statement" | "Smart"
  >("Balance");

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const timestamp = () =>
    new Date().toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const sendChatRequest = async (
    text: string,
    overrideCreds: boolean = false
  ) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    // Don't show "LOGIN_AUTH" text from user
    if (!(overrideCreds && trimmed === "LOGIN_AUTH")) {
      setMessages((prev) => [
        ...prev,
        { from: "user", text: trimmed, time: timestamp() },
      ]);
    }

    setInput("");
    setLoading(true);

    const body = {
      message: trimmed,
      account_number:
        overrideCreds || isVerified ? accountNumber || null : null,
      pin: overrideCreds || isVerified ? pin || null : null,
    };

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      const reply: string =
        data.error || data.reply || "Something went wrong on the server.";

      // Detect PIN verification
      if (reply.toLowerCase().includes("pin verified")) {
        setIsVerified(true);
        const nameMatch = reply.match(/Hello\s(.+?)!/);
        if (nameMatch) setUserName(nameMatch[1]);
      }

      // Detect balance like ₹28,150
      const balMatch = reply.match(/₹([\d,]+)/);
      if (balMatch) {
        const val = parseInt(balMatch[1].replace(/,/g, ""), 10);
        if (!Number.isNaN(val)) setBalance(val);
      }

      setMessages((prev) => [
        ...prev,
        { from: "bot", text: reply, time: timestamp() },
      ]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          from: "bot",
          text: "Server error. Please try again.",
          time: timestamp(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const login = async () => {
    // client-side validation
    const acValid = /^[A-Z]{3}[0-9]{4}$/.test(accountNumber);
    const pinValid = /^[0-9]{4}$/.test(pin);
    if (!acValid || !pinValid) return;

    // Just call login_auth – no extra auto messages to bot
    setMessages((prev) => [
      ...prev,
      { from: "user", text: "Login Attempt", time: timestamp() },
    ]);

    await sendChatRequest("LOGIN_AUTH", true);
  };

  const handleQuickPrompt = (msg: string) => {
    if (!isVerified) return;
    sendChatRequest(msg);
  };

  return (
    <div className="h-screen w-full flex items-center justify-center bg-slate-900 text-white">
      <div className="w-[95%] max-w-3xl h-[92vh] bg-slate-800 rounded-2xl shadow-xl flex flex-col border border-slate-700">
        {/* Header */}
        <div className="px-6 py-3 border-b border-slate-700 flex items-center justify-between">
          <div>
            <h1 className="font-semibold text-sm md:text-base">
              ABC Bank – AI Assistant
            </h1>
            <p className="text-xs text-slate-400">Secure Banking with AI</p>
          </div>
        </div>

        {/* Login section */}
        {!isVerified && (
          <div className="px-4 py-3 border-b border-slate-700 bg-slate-900 space-y-3">
            <div className="flex gap-2">
              <input
                placeholder="Account (ABC1234)"
                className={`flex-1 px-3 py-2 rounded-md bg-slate-800 border ${
                  accountNumber && !/^[A-Z]{3}[0-9]{4}$/.test(accountNumber)
                    ? "border-red-500"
                    : "border-slate-700"
                }`}
                maxLength={7}
                value={accountNumber}
                onChange={(e) =>
                  setAccountNumber(e.target.value.toUpperCase())
                }
              />
              <input
                placeholder="PIN"
                type="password"
                className={`w-24 px-3 py-2 rounded-md bg-slate-800 border ${
                  pin && !/^[0-9]{4}$/.test(pin)
                    ? "border-red-500"
                    : "border-slate-700"
                }`}
                maxLength={4}
                value={pin}
                onChange={(e) =>
                  setPin(e.target.value.replace(/\D/g, ""))
                }
              />
            </div>

            {accountNumber && !/^[A-Z]{3}[0-9]{4}$/.test(accountNumber) && (
              <p className="text-xs text-red-400">
                Invalid account format, expected ABC1234.
              </p>
            )}

            {pin && !/^[0-9]{4}$/.test(pin) && (
              <p className="text-xs text-red-400">
                PIN must be exactly 4 digits.
              </p>
            )}

            <button
              className="w-full py-2 bg-emerald-600 rounded-md hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={
                loading ||
                !/^[A-Z]{3}[0-9]{4}$/.test(accountNumber) ||
                !/^[0-9]{4}$/.test(pin)
              }
              onClick={login}
            >
              Proceed Securely
            </button>
          </div>
        )}

        {/* Auth summary */}
        {isVerified && (
          <div className="px-4 py-2 bg-slate-900 border-b border-slate-700 flex justify-between text-xs text-slate-300">
            <span>👤 {userName || "Verified User"}</span>
            <span>💳 {accountNumber}</span>
            <span>
              💰{" "}
              {balance !== null
                ? `₹${balance.toLocaleString("en-IN")}`
                : "₹---"}
            </span>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${
                m.from === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div>
                <div
                  className={`px-4 py-2 rounded-2xl text-sm max-w-[95%] ${
                    m.from === "user"
                      ? "bg-emerald-600"
                      : "bg-slate-700 border border-slate-600 whitespace-pre-line"
                  }`}
                >
                  {m.text}
                </div>

                <p className="text-[10px] text-slate-400 mt-1">{m.time}</p>
              </div>
            </div>
          ))}

          {loading && (
            <div className="bg-slate-700 px-3 py-1.5 rounded-xl text-xs text-slate-300 animate-pulse w-fit">
              Bot is typing…
            </div>
          )}

          <div ref={messagesEndRef}></div>
        </div>

        {/* Tabs + quick prompts */}
        {isVerified && (
          <div className="bg-slate-900 border-t border-slate-700">
            {/* Tabs */}
            <div className="flex justify-around text-[11px] md:text-xs text-slate-300 py-2 bg-slate-800">
              {["Balance", "Deposit", "Withdraw", "Transfer", "Statement", "Smart"].map(
                (tab) => (
                  <button
                    key={tab}
                    className={`px-2 py-1 rounded-full ${
                      activeTab === tab
                        ? "bg-emerald-600 text-white"
                        : "hover:text-emerald-400"
                    }`}
                    onClick={() =>
                      setActiveTab(
                        tab as
                          | "Balance"
                          | "Deposit"
                          | "Withdraw"
                          | "Transfer"
                          | "Statement"
                          | "Smart"
                      )
                    }
                  >
                    {tab}
                  </button>
                )
              )}
            </div>

            {/* Tab buttons */}
            <div className="flex flex-wrap gap-2 p-2 justify-center">
              {activeTab === "Balance" && (
                <button
                  onClick={() => handleQuickPrompt("Check my balance")}
                  className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                >
                  Check balance
                </button>
              )}

              {activeTab === "Deposit" && (
                <>
                  <button
                    onClick={() => handleQuickPrompt("Deposit 100")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    +₹100
                  </button>
                  <button
                    onClick={() => handleQuickPrompt("Deposit 500")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    +₹500
                  </button>
                  <button
                    onClick={() => handleQuickPrompt("Deposit 1000")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    +₹1000
                  </button>
                </>
              )}

              {activeTab === "Withdraw" && (
                <>
                  <button
                    onClick={() => handleQuickPrompt("Withdraw 100")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    ₹100
                  </button>
                  <button
                    onClick={() => handleQuickPrompt("Withdraw 200")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    ₹200
                  </button>
                  <button
                    onClick={() => handleQuickPrompt("Withdraw 500")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    ₹500
                  </button>
                </>
              )}

              {activeTab === "Transfer" && (
                <>
                  <button
                    onClick={() =>
                      handleQuickPrompt("Transfer 50 to ABC5678")
                    }
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    ₹50 → ABC5678
                  </button>
                  <button
                    onClick={() =>
                      handleQuickPrompt("Transfer 100 to ABC5678")
                    }
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    ₹100 → ABC5678
                  </button>
                </>
              )}

              {activeTab === "Statement" && (
                <>
                  <button
                    onClick={() => handleQuickPrompt("Mini statement")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    Mini Statement
                  </button>
                  <button
                    onClick={() => handleQuickPrompt("Transaction history")}
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    Full history
                  </button>
                </>
              )}

              {activeTab === "Smart" && (
                <>
                  <button
                    onClick={() =>
                      handleQuickPrompt("Where did I spend most this week?")
                    }
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    Spending insights
                  </button>
                  <button
                    onClick={() =>
                      handleQuickPrompt("Suggest how to save money")
                    }
                    className="text-xs px-3 py-1 bg-slate-700 rounded-md hover:bg-emerald-600 whitespace-nowrap"
                  >
                    Savings tips
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Chat input */}
        {isVerified && (
          <div className="px-4 py-3 border-t border-slate-700 flex gap-2">
            <input
              className="flex-1 rounded-full px-3 py-2 bg-slate-900 border border-slate-600 text-sm"
              placeholder="Type your banking request"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) =>
                e.key === "Enter" && sendChatRequest(input)
              }
            />
            <button
              className="rounded-full bg-emerald-600 px-4 py-2 disabled:opacity-50"
              disabled={loading}
              onClick={() => sendChatRequest(input)}
            >
              Send
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
