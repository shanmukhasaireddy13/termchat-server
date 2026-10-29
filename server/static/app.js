/**
 * termchat Web Client Application
 * Supports real-time text chat, image uploading, clipboard image pasting (Ctrl+V),
 * drag-and-drop images, presence tracking, and full mobile responsiveness.
 */

(() => {
  const state = {
    username: localStorage.getItem("termchat_web_user") || "WebUser_" + Math.floor(Math.random() * 1000),
    ws: null,
    selectedFile: null,
    users: [],
    isSubmitting: false,
  };

  // DOM Elements
  const appContainer = document.getElementById("app");
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const onlineCount = document.getElementById("onlineCount");
  const usersButton = document.getElementById("usersButton");
  const usersSidebar = document.getElementById("usersSidebar");
  const sidebarBackdrop = document.getElementById("sidebarBackdrop");
  const closeSidebarBtn = document.getElementById("closeSidebarBtn");
  const sidebarUserCount = document.getElementById("sidebarUserCount");
  const terminalList = document.getElementById("terminalList");
  const webList = document.getElementById("webList");

  const messagesList = document.getElementById("messagesList");
  const dropZone = document.getElementById("dropZone");
  const dropOverlay = document.getElementById("dropOverlay");

  const imagePreviewBar = document.getElementById("imagePreviewBar");
  const previewImg = document.getElementById("previewImg");
  const previewFilename = document.getElementById("previewFilename");
  const cancelUploadBtn = document.getElementById("cancelUploadBtn");

  const chatForm = document.getElementById("chatForm");
  const messageInput = document.getElementById("messageInput");
  const sendBtn = document.getElementById("sendBtn");
  const attachBtn = document.getElementById("attachBtn");
  const askAiBtn = document.getElementById("askAiBtn");
  const fileInput = document.getElementById("fileInput");

  const nicknameBtn = document.getElementById("nicknameBtn");
  const displayNickname = document.getElementById("displayNickname");
  const headerNickBtn = document.getElementById("headerNickBtn");
  const headerNickname = document.getElementById("headerNickname");

  const lightboxModal = document.getElementById("lightboxModal");
  const lightboxImg = document.getElementById("lightboxImg");
  const closeLightbox = document.getElementById("closeLightbox");

  // Display initial nickname
  function updateDisplayedNicknames(name) {
    if (displayNickname) displayNickname.textContent = name;
    if (headerNickname) headerNickname.textContent = name;
  }
  updateDisplayedNicknames(state.username);

  // Nickname change dialog
  function promptNicknameChange() {
    const val = prompt("Enter your display nickname:", state.username);
    if (val && val.trim() && val.trim() !== state.username) {
      state.username = val.trim();
      localStorage.setItem("termchat_web_user", state.username);
      updateDisplayedNicknames(state.username);
      if (state.ws) state.ws.close();
    }
  }

  if (nicknameBtn) nicknameBtn.addEventListener("click", promptNicknameChange);
  if (headerNickBtn) headerNickBtn.addEventListener("click", promptNicknameChange);

  // Mobile Sidebar Toggle & Backdrop
  function setSidebarOpen(open) {
    const willOpen = open !== undefined ? open : !usersSidebar.classList.contains("open");
    if (willOpen) {
      usersSidebar.classList.add("open");
      if (sidebarBackdrop) sidebarBackdrop.classList.remove("hidden");
    } else {
      usersSidebar.classList.remove("open");
      if (sidebarBackdrop) sidebarBackdrop.classList.add("hidden");
    }
  }

  usersButton.addEventListener("click", () => setSidebarOpen());
  closeSidebarBtn.addEventListener("click", () => setSidebarOpen(false));
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));
  }

  // Textarea auto-resize
  function adjustTextareaHeight() {
    messageInput.style.height = "auto";
    const newHeight = Math.min(messageInput.scrollHeight, 120);
    messageInput.style.height = Math.max(newHeight, 24) + "px";
  }

  messageInput.addEventListener("input", adjustTextareaHeight);

  // Mobile Visual Viewport Handling (Fixes virtual keyboard hiding input bar)
  if (window.visualViewport && appContainer) {
    const handleViewportChange = () => {
      appContainer.style.height = `${window.visualViewport.height}px`;
      scrollToBottom();
    };
    window.visualViewport.addEventListener("resize", handleViewportChange);
    window.visualViewport.addEventListener("scroll", handleViewportChange);
  }

  messageInput.addEventListener("focus", () => {
    setTimeout(scrollToBottom, 200);
  });

  // WebSocket Connection
  function getWsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const user = encodeURIComponent(state.username);
    return `${proto}//${host}/ws?username=${user}&client_type=web&device_info=Web%20Browser`;
  }

  function connectWs() {
    const url = getWsUrl();
    statusDot.className = "dot";
    statusText.textContent = "Connecting...";

    try {
      state.ws = new WebSocket(url);
    } catch (e) {
      setTimeout(connectWs, 3000);
      return;
    }

    state.ws.onopen = () => {
      statusDot.className = "dot connected";
      statusText.textContent = "Online";
    };

    state.ws.onclose = () => {
      statusDot.className = "dot disconnected";
      statusText.textContent = "Reconnecting...";
      setTimeout(connectWs, 2500);
    };

    state.ws.onerror = () => {
      state.ws.close();
    };

    state.ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleMessage(msg);
      } catch (err) {
        console.error("Message parse error:", err);
      }
    };
  }

  function handleMessage(msg) {
    switch (msg.type) {
      case "history":
        if (Array.isArray(msg.messages)) {
          msg.messages.forEach((m) => renderMessage(m));
          scrollToBottom();
        }
        break;

      case "user_list":
        updateUsers(msg.users || []);
        break;

      case "chat":
      case "image":
      case "ai":
        renderMessage(msg);
        scrollToBottom();
        break;

      case "system":
        renderSystem(msg);
        scrollToBottom();
        break;

      case "ping":
        if (state.ws && state.ws.readyState === WebSocket.OPEN) {
          state.ws.send(JSON.stringify({ type: "pong" }));
        }
        break;
    }
  }

  function updateUsers(users) {
    state.users = users;
    const total = users.length;
    onlineCount.textContent = total;
    sidebarUserCount.textContent = total;

    const terms = users.filter((u) => u.client_type === "terminal");
    const webs = users.filter((u) => u.client_type === "web");

    renderList(terminalList, terms, "No terminals connected");
    renderList(webList, webs, "No web users connected");
  }

  function renderList(container, list, emptyText) {
    container.innerHTML = "";
    if (!list.length) {
      container.innerHTML = `<li class="empty-li">${emptyText}</li>`;
      return;
    }
    list.forEach((u) => {
      const li = document.createElement("li");
      li.className = "user-li";
      li.innerHTML = `
        <span class="user-li-name">${escapeHtml(u.username)}</span>
        <span class="user-li-device">${escapeHtml(u.device_info || "Online")}</span>
      `;
      container.appendChild(li);
    });
  }

  function renderMessage(msg) {
    const isAi = msg.type === "ai" || msg.client_type === "ai";
    const isMe = msg.sender === state.username && msg.client_type === "web";
    const isTerm = msg.client_type === "terminal";

    const row = document.createElement("div");
    let originClass = "web";
    if (isAi) originClass = "ai";
    else if (isTerm) originClass = "terminal";
    row.className = `msg-row ${originClass} ${isMe ? "is-me" : ""}`;

    const time = formatTime(msg.timestamp);
    let badge = `<span class="msg-badge badge-web">🌐 WEB</span>`;
    if (isAi) {
      badge = `<span class="msg-badge badge-ai">🤖 AI ASSISTANT</span>`;
    } else if (isTerm) {
      badge = `<span class="msg-badge badge-term">💻 TERMINAL</span>`;
    }

    let contentHtml = "";
    if (msg.type === "image") {
      contentHtml = `
        <div class="image-card" onclick="window.viewLightbox('${msg.image_url}')">
          <img src="${msg.image_url}" alt="Uploaded image" loading="lazy" />
          <div class="image-card-caption">
            <span>📷 ${escapeHtml(msg.filename || "image.png")}</span>
            <a href="${msg.image_url}" target="_blank" class="image-link-btn" onclick="event.stopPropagation()">Download</a>
          </div>
        </div>
      `;
    } else {
      let formattedText = escapeHtml(msg.text || "");
      // Markdown code blocks formatting
      if (formattedText.includes("```")) {
        formattedText = formattedText.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
          return `<pre><code>${code.trim()}</code></pre>`;
        });
      }
      contentHtml = `<div class="msg-bubble">${formattedText}</div>`;
    }

    row.innerHTML = `
      <div class="msg-meta">
        <span class="msg-sender">${escapeHtml(msg.sender || "User")}</span>
        ${badge}
        <span class="msg-time">${time}</span>
      </div>
      ${contentHtml}
    `;

    messagesList.appendChild(row);
  }

  function renderSystem(msg) {
    const row = document.createElement("div");
    row.className = "sys-row";
    row.innerHTML = `<div class="sys-pill">⚙️ ${escapeHtml(msg.text || "")}</div>`;
    messagesList.appendChild(row);
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messagesList.scrollTop = messagesList.scrollHeight;
    });
  }

  // File Upload Handling
  attachBtn.addEventListener("click", () => fileInput.click());

  // Ask AI Button Helper
  askAiBtn.addEventListener("click", () => {
    messageInput.value = "/ai ";
    messageInput.focus();
    adjustTextareaHeight();
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleSelectedImage(e.target.files[0]);
    }
  });

  function handleSelectedImage(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please select an image file (PNG, JPG, GIF, WebP).");
      return;
    }
    state.selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      previewImg.src = e.target.result;
      previewFilename.textContent = file.name || "image.png";
      imagePreviewBar.classList.remove("hidden");
      scrollToBottom();
    };
    reader.readAsDataURL(file);
  }

  cancelUploadBtn.addEventListener("click", () => {
    state.selectedFile = null;
    fileInput.value = "";
    imagePreviewBar.classList.add("hidden");
  });

  // Drag and Drop (Desktop)
  window.addEventListener("dragenter", (e) => {
    if (hasImageFiles(e)) dropOverlay.classList.remove("hidden");
  });

  window.addEventListener("dragleave", (e) => {
    if (e.relatedTarget === null) dropOverlay.classList.add("hidden");
  });

  window.addEventListener("dragover", (e) => e.preventDefault());

  window.addEventListener("drop", (e) => {
    e.preventDefault();
    dropOverlay.classList.add("hidden");
    if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleSelectedImage(e.dataTransfer.files[0]);
    }
  });

  function hasImageFiles(e) {
    if (!e.dataTransfer || !e.dataTransfer.types) return false;
    return e.dataTransfer.types.includes("Files");
  }

  // Clipboard Paste (Ctrl+V) for screenshots & images
  window.addEventListener("paste", (e) => {
    const items = e.clipboardData ? e.clipboardData.items : null;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf("image") !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          handleSelectedImage(file);
          e.preventDefault();
          break;
        }
      }
    }
  });

  // Sending Chat or Image
  async function submitChat() {
    if (state.isSubmitting) return;

    const hasFile = !!state.selectedFile;
    const text = messageInput.value.trim();

    if (!hasFile && !text) return;

    state.isSubmitting = true;

    // 1. If an image is staged, upload it
    if (hasFile) {
      const fileToUpload = state.selectedFile;
      state.selectedFile = null;
      imagePreviewBar.classList.add("hidden");
      fileInput.value = "";

      const formData = new FormData();
      formData.append("file", fileToUpload);
      formData.append("sender", state.username);
      formData.append("client_type", "web");

      try {
        const resp = await fetch("/api/upload", {
          method: "POST",
          body: formData,
        });
        if (!resp.ok) {
          alert("Image upload failed.");
        }
      } catch (err) {
        console.error("Upload error:", err);
      }
    }

    // 2. If text was entered, send via WebSocket
    if (text) {
      if (!state.ws || state.ws.readyState !== WebSocket.OPEN) {
        alert("Not connected to server. Please wait for reconnection...");
        state.isSubmitting = false;
        return;
      }
      state.ws.send(JSON.stringify({ type: "chat", text: text }));
      messageInput.value = "";
      adjustTextareaHeight();
    }

    state.isSubmitting = false;
    messageInput.focus();
  }

  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitChat();
  });

  messageInput.addEventListener("keydown", (e) => {
    // On desktop Enter sends; on mobile Enter or Send button sends
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitChat();
    }
  });

  // Lightbox
  window.viewLightbox = (url) => {
    lightboxImg.src = url;
    lightboxModal.classList.remove("hidden");
  };

  closeLightbox.addEventListener("click", () => lightboxModal.classList.add("hidden"));
  lightboxModal.addEventListener("click", (e) => {
    if (e.target === lightboxModal) lightboxModal.classList.add("hidden");
  });

  // Helpers
  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function formatTime(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return "";
    }
  }

  connectWs();
})();
