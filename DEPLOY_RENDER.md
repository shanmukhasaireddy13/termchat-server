# 🌐 Deploying the termchat Server to Render (Free & Fast)

[Render](https://render.com) is the recommended platform to run your online chat server because it supports persistent WebSockets (`wss://`), HTTP file uploads, and static website hosting 24/7 on their free tier.

Once deployed, your server will have an online URL like:
`https://my-termchat.onrender.com`

---

## Method 1: Deploy with GitHub (Recommended - 2 Minutes)

### Step 1: Push this repository to GitHub
1. Create a new repository on [GitHub](https://github.com/new) (e.g. `my-termchat-server`).
2. In your local project folder, push the code:
   ```bash
   git init
   git add .
   git commit -m "Initial commit for termchat server and client"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/my-termchat-server.git
   git push -u origin main
   ```

### Step 2: Create a Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** > **Web Service**.
2. Select **Build and deploy from a Git repository** and connect your GitHub repository.
3. Configure the following fields:
   - **Name**: `my-termchat` (or any name you like)
   - **Region**: Any (e.g. Frankfurt, Oregon, Ohio, Singapore)
   - **Branch**: `main`
   - **Root Directory**: `server`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free`
4. Click **Create Web Service**.

Render will build and deploy your service in about 1-2 minutes.
Once done, you will see your live URL at the top:
👉 `https://my-termchat.onrender.com`

---

## Method 2: Deploy with Docker on Render

If you prefer container deployment:
1. When creating the Web Service on Render, choose **Runtime**: `Docker`.
2. Set **Docker Context**: `server`
3. Set **Dockerfile Path**: `server/Dockerfile`
4. Click **Deploy**.

---

## 💻 How Clients Connect

### 1. The Web Client (Browser)
Anyone with the link can open the URL in any browser:
```text
https://my-termchat.onrender.com
```
They will see:
- Real-time messages sent from the terminal.
- A text box to reply back to the terminal.
- An **Attach Image** button, **Drag & Drop** area, and **Ctrl+V clipboard pasting** to send screenshots/images directly to the terminal!

---

### 2. The Terminal Client (Python Package)
Anyone with Python installed on **Linux**, **Raspberry Pi**, **Windows**, or **macOS** can install the client package from PyPI:

```bash
pip install termchat-client
```

And connect:
```bash
termchat --server https://my-termchat.onrender.com --name Alice
```
*(Or via python: `python -m termchat --server https://my-termchat.onrender.com`)*

#### Save URL Once:
Save your Render URL permanently to `~/.termchat.json`:
```bash
termchat --set-server https://my-termchat.onrender.com
```
After running that once, you can connect anytime with just:
```bash
termchat
```
or
```bash
python -m termchat
```
No UI changes — it is a standard command line interface. You type text, press Enter to send, and receive text replies and image previews right in your terminal!
