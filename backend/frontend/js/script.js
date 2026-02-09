const API_BASE = "";

// ================= UPLOAD FILE =================
document.getElementById("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];
    if (!file) return;

    setResult("⏳ Processing uploaded file...");

    const fd = new FormData();
    fd.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/process`, {
            method: "POST",
            body: fd
        });

        if (!res.ok) {
            setResult("❌ Error processing file");
            return;
        }

        const data = await res.json();
        renderResult(data);
    } catch (err) {
        setResult("❌ Server not responding");
    }
});

// ================= PROCESS VIDEO LINK =================
async function processLink() {
    const url = document.getElementById("videoLink").value.trim();
    if (!url) {
        alert("Please paste a video link");
        return;
    }

    setResult("⏳ Downloading & analyzing video...");

    try {
        const res = await fetch(`${API_BASE}/process_link`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url })
        });

        if (!res.ok) {
            setResult("❌ Error processing video link");
            return;
        }

        const data = await res.json();
        renderResult(data);
    } catch (err) {
        setResult("❌ Server not responding");
    }
}

// ================= RENDER RESULT =================
function renderResult(data) {
    let html = "";

    // -------- SUMMARY --------
    if (data.content_summary) {
        html += `
            <h4>📘 Video Summary</h4>
            <p>${data.content_summary}</p>
        `;
    }

    // -------- PEOPLE --------
    html += `
        <h4>👥 People Analysis</h4>
        <p>
            Total People: <b>${data.unique_people ?? 0}</b><br>
            Male: <b>${data.male ?? 0}</b> |
            Female: <b>${data.female ?? 0}</b>
        </p>
    `;

    // -------- OBJECTS --------
    if (data.visual_objects && data.visual_objects.length) {
        html += `
            <h4>🧱 Objects Detected</h4>
            <p>${data.visual_objects.join(", ")}</p>
        `;
    }

    document.getElementById("result").innerHTML = html;
}

// ================= CHAT BOT =================
async function askBot() {
    const q = document.getElementById("userQuestion").value.trim();
    if (!q) return;

    appendChat("You", q);

    try {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: q })
        });

        if (!res.ok) {
            appendChat("VideoGPT", "❌ Error answering question");
            return;
        }

        const data = await res.json();
        appendChat("VideoGPT", data.reply);
    } catch {
        appendChat("VideoGPT", "❌ Server not responding");
    }

    document.getElementById("userQuestion").value = "";
}

// ================= CHAT UI =================
function appendChat(sender, text) {
    const box = document.getElementById("chatMessages");
    box.innerHTML += `<p><b>${sender}:</b> ${text}</p>`;
    box.scrollTop = box.scrollHeight;
}

// ================= UTIL =================
function setResult(text) {
    document.getElementById("result").innerHTML = `<p>${text}</p>`;
}
