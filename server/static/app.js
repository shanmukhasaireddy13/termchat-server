/**
 * termchat Web Client Application
 * Real-time terminal ↔ web chat bridge with image sharing, AI assistance,
 * onboarding name modal, and dedicated mobile ergonomics.
 */

(() => {
  const state = {
    username: localStorage.getItem("termchat_web_user") || "",
    ws: null,
    selectedFile: null,
    users: [],
    isSubmitting: false,
    hasJoined: false,
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

  const joinModal = document.getElementById("joinModal");
  const joinModalTitle = document.getElementById("joinModalTitle");
  const joinModalSubtitle = document.getElementById("joinModalSubtitle");
  const joinForm = document.getElementById("joinForm");
  const joinNameInput = document.getElementById("joinNameInput");
  const joinSubmitBtn = document.getElementById("joinSubmitBtn");

  const lightboxModal = document.getElementById("lightboxModal");
  const lightboxImg = document.getElementById("lightboxImg");
  const closeLightbox = document.getElementById("closeLightbox");

  // Display initial nickname
  function updateDisplayedNicknames(name) {
    const cleanName = name || "WebUser";
    if (displayNickname) displayNickname.textContent = cleanName;
    if (headerNickname) headerNickname.textContent = cleanName;
  }

  // Join / Edit Name Modal Dialog
  function showJoinModal(isEditing = false) {
    if (!joinModal) return;
    if (isEditing) {
      if (joinModalTitle) joinModalTitle.textContent = "Change Display Name";
      if (joinModalSubtitle) joinModalSubtitle.textContent = "Update your name across connected terminals and web clients.";
      if (joinSubmitBtn) joinSubmitBtn.textContent = "Save & Update";
    } else {
      if (joinModalTitle) joinModalTitle.textContent = "Welcome to termchat";
      if (joinModalSubtitle) joinModalSubtitle.textContent = "Enter your display name to start chatting with connected terminals and web users.";
      if (joinSubmitBtn) joinSubmitBtn.textContent = "Join Chat ➜";
    }

    const current = state.username || localStorage.getItem("termchat_web_user") || "";
    if (joinNameInput) {
      joinNameInput.value = current.startsWith("WebUser_") ? "" : current;
      joinNameInput.placeholder = "e.g. Alex, Shanmukha, Bob";
    }

    joinModal.classList.remove("hidden");
    setTimeout(() => {
      if (joinNameInput) {
        joinNameInput.focus();
        if (joinNameInput.value) joinNameInput.select();
      }
    }, 80);
  }

  function hideJoinModal() {
    if (joinModal) joinModal.classList.add("hidden");
  }

  if (joinForm) {
    joinForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const val = (joinNameInput ? joinNameInput.value : "").trim();
      if (!val) {
        if (joinNameInput) {
          joinNameInput.classList.add("input-error");
          joinNameInput.focus();
          setTimeout(() => joinNameInput.classList.remove("input-error"), 1500);
        }
        return;
      }

      const previousName = state.username;
      state.username = val;
      state.hasJoined = true;
      localStorage.setItem("termchat_web_user", val);
      updateDisplayedNicknames(val);
      hideJoinModal();

      if (!state.ws) {
        connectWs();
      } else if (previousName !== val) {
        // Reconnect so server and others receive the updated username
        state.ws.close();
      }

      setTimeout(() => {
        if (messageInput) messageInput.focus();
      }, 150);
    });
  }

  if (nicknameBtn) nicknameBtn.addEventListener("click", () => showJoinModal(true));
  if (headerNickBtn) headerNickBtn.addEventListener("click", () => showJoinModal(true));

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

  if (usersButton) usersButton.addEventListener("click", () => setSidebarOpen());
  if (closeSidebarBtn) closeSidebarBtn.addEventListener("click", () => setSidebarOpen(false));
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", () => setSidebarOpen(false));
  }

  // Textarea auto-resize
  function adjustTextareaHeight() {
    if (!messageInput) return;
    messageInput.style.height = "auto";
    const newHeight = Math.min(messageInput.scrollHeight, 120);
    messageInput.style.height = Math.max(newHeight, 32) + "px";
  }

  if (messageInput) {
    messageInput.addEventListener("input", adjustTextareaHeight);
  }

  // Viewport Height Synchronizer (Fixes virtual mobile keyboard pushing layout offscreen)
  function syncViewportLayout() {
    const vh = window.visualViewport ? window.visualViewport.height : window.innerHeight;
    document.documentElement.style.setProperty("--app-height", `${vh}px`);
    if (appContainer) {
      appContainer.style.height = `${vh}px`;
    }
    scrollToBottom();
  }

  syncViewportLayout();
  window.addEventListener("resize", syncViewportLayout);
  window.addEventListener("orientationchange", () => setTimeout(syncViewportLayout, 150));

  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", syncViewportLayout);
    window.visualViewport.addEventListener("scroll", syncViewportLayout);
  }

  if (messageInput) {
    messageInput.addEventListener("focus", () => {
      setTimeout(syncViewportLayout, 80);
      setTimeout(syncViewportLayout, 250);
      setTimeout(scrollToBottom, 300);
    });
  }

  // WebSocket Connection
  function getWsUrl() {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const user = encodeURIComponent(state.username || "WebUser");
    return `${proto}//${host}/ws?username=${user}&client_type=web&device_info=Web%20Browser`;
  }

  function connectWs() {
    if (!state.username) return;

    const url = getWsUrl();
    if (statusDot) statusDot.className = "dot";
    if (statusText) statusText.textContent = "Connecting...";

    try {
      state.ws = new WebSocket(url);
    } catch (e) {
      setTimeout(connectWs, 3000);
      return;
    }

    state.ws.onopen = () => {
      if (statusDot) statusDot.className = "dot connected";
      if (statusText) statusText.textContent = "Online";
    };

    state.ws.onclose = () => {
      if (statusDot) statusDot.className = "dot disconnected";
      if (statusText) statusText.textContent = "Reconnecting...";
      setTimeout(connectWs, 2500);
    };

    state.ws.onerror = () => {
      if (state.ws) state.ws.close();
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
    if (onlineCount) onlineCount.textContent = total;
    if (sidebarUserCount) sidebarUserCount.textContent = total;

    const terms = users.filter((u) => u.client_type === "terminal");
    const webs = users.filter((u) => u.client_type === "web");

    renderList(terminalList, terms, "No terminals connected");
    renderList(webList, webs, "No web users connected");
  }

  function renderList(container, list, emptyText) {
    if (!container) return;
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
    if (!messagesList) return;
    const isAi = msg.type === "ai" || msg.client_type === "ai";
    const isMe = msg.sender === state.username && msg.client_type === "web";
    const isTerm = msg.client_type === "terminal";

    const row = document.createElement("div");
    let originClass = "web";
    if (isAi) originClass = "ai";
    else if (isTerm) originClass = "terminal";
    row.className = `msg-row ${originClass} ${isMe ? "is-me" : ""}`;

    const time = formatTime(msg.timestamp);
    let badge = `<span class="msg-badge badge-web">WEB</span>`;
    if (isAi) {
      badge = `<span class="msg-badge badge-ai">AI</span>`;
    } else if (isTerm) {
      badge = `<span class="msg-badge badge-term">TERMINAL</span>`;
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
    if (!messagesList) return;
    const row = document.createElement("div");
    row.className = "sys-row";
    row.innerHTML = `<div class="sys-pill">⚙️ ${escapeHtml(msg.text || "")}</div>`;
    messagesList.appendChild(row);
  }

  function scrollToBottom() {
    if (!messagesList) return;
    requestAnimationFrame(() => {
      messagesList.scrollTop = messagesList.scrollHeight;
    });
  }

  // File Upload Handling
  if (attachBtn && fileInput) {
    attachBtn.addEventListener("click", () => fileInput.click());
  }

  if (askAiBtn && messageInput) {
    askAiBtn.addEventListener("click", () => {
      messageInput.value = "/ai ";
      messageInput.focus();
      adjustTextareaHeight();
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files[0]) {
        handleSelectedImage(e.target.files[0]);
      }
    });
  }

  function handleSelectedImage(file) {
    if (!file.type.startsWith("image/")) {
      alert("Please select an image file (PNG, JPG, GIF, WebP).");
      return;
    }
    state.selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
      if (previewImg) previewImg.src = e.target.result;
      if (previewFilename) previewFilename.textContent = file.name || "image.png";
      if (imagePreviewBar) imagePreviewBar.classList.remove("hidden");
      scrollToBottom();
    };
    reader.readAsDataURL(file);
  }

  if (cancelUploadBtn) {
    cancelUploadBtn.addEventListener("click", () => {
      state.selectedFile = null;
      if (fileInput) fileInput.value = "";
      if (imagePreviewBar) imagePreviewBar.classList.add("hidden");
    });
  }

  // Drag and Drop (Desktop)
  window.addEventListener("dragenter", (e) => {
    if (hasImageFiles(e) && dropOverlay) dropOverlay.classList.remove("hidden");
  });

  window.addEventListener("dragover", (e) => {
    e.preventDefault();
  });

  if (dropOverlay) {
    dropOverlay.addEventListener("dragleave", (e) => {
      if (e.relatedTarget === null || !dropOverlay.contains(e.relatedTarget)) {
        dropOverlay.classList.add("hidden");
      }
    });

    dropOverlay.addEventListener("drop", (e) => {
      e.preventDefault();
      dropOverlay.classList.add("hidden");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleSelectedImage(e.dataTransfer.files[0]);
      }
    });
  }

  function hasImageFiles(e) {
    if (!e.dataTransfer || !e.dataTransfer.types) return false;
    return Array.from(e.dataTransfer.types).includes("Files");
  }

  // Clipboard Paste Support (Ctrl+V / Cmd+V)
  window.addEventListener("paste", (e) => {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf("image") !== -1) {
        const blob = items[i].getAsFile();
        const file = new File([blob], `clipboard-${Date.now()}.png`, { type: blob.type });
        handleSelectedImage(file);
        break;
      }
    }
  });

  // Sending Messages
  async function submitChat() {
    if (state.isSubmitting) return;

    const hasFile = !!state.selectedFile;
    const text = messageInput ? messageInput.value.trim() : "";

    if (!hasFile && !text) return;

    state.isSubmitting = true;

    // 1. If an image is staged, upload it
    if (hasFile) {
      const fileToUpload = state.selectedFile;
      state.selectedFile = null;
      if (imagePreviewBar) imagePreviewBar.classList.add("hidden");
      if (fileInput) fileInput.value = "";

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
      if (messageInput) {
        messageInput.value = "";
        adjustTextareaHeight();
      }
    }

    state.isSubmitting = false;
    if (messageInput) messageInput.focus();
  }

  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      submitChat();
    });
  }

  if (messageInput) {
    messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        submitChat();
      }
    });
  }

  // Lightbox
  window.viewLightbox = (url) => {
    if (lightboxImg && lightboxModal) {
      lightboxImg.src = url;
      lightboxModal.classList.remove("hidden");
    }
  };

  if (closeLightbox && lightboxModal) {
    closeLightbox.addEventListener("click", () => lightboxModal.classList.add("hidden"));
    lightboxModal.addEventListener("click", (e) => {
      if (e.target === lightboxModal) lightboxModal.classList.add("hidden");
    });
  }

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

  // Startup: Ask name before entering chat
  showJoinModal(false);
})();
