<p align="center">
  <img src="extension/icons/icon-master.png" width="96" height="96" alt="PasteFlick">
</p>

<h1 align="center">PasteFlick</h1>

<p align="center">
  Copy from ChatGPT. Flick it into the last app you were using.
</p>

<p align="center">
  <strong>Windows.</strong> Brave, Chrome, Edge, Chromium, and Arc. ChatGPT only.<br>
  Not affiliated with OpenAI.
</p>

Long chats fight the clipboard. PasteFlick sits on the conversation as one chip: take a highlight, or the thread you can see, then **Copy**, **Save**, or **Fling** it into Word, Notes, Cursor — wherever you just were.

It copies what is on the page. Turns ChatGPT has not rendered yet are not in the copy.

Repo: [github.com/HeadAroundIt/pasteflick](https://github.com/HeadAroundIt/pasteflick)

---

## What you get

One chip under the chat title. Highlight a passage, or take the visible thread — then **Copy**, **Save**, or **Fling**. ChatGPT’s own buttons stay where they are.

Pin any message. **Copy from PasteFlick** starts at that pin, so you can take the rest of the conversation without dragging a selection.

The toolbar popup is there when you want it:

- **Copy selection** — the highlight you made
- **Copy thread** — the conversation currently on the page
- **Copy from PasteFlick** — from your pin onward

Choose where the text goes:

- **Clipboard** — ready to paste when you are
- **Fling** — into the last app you were in
- **File** — Markdown or PDF, in a folder you pick

The first time you copy, allow clipboard access if ChatGPT or the browser asks.

---

## Support

PasteFlick is free to use. If it saves you time or frustration, a $5 tip helps support future updates and more useful free apps.

No pressure... just genuine appreciation!

<p align="center">
  <a href="https://ko-fi.com/ryandunham"><img src="extension/icons/tip5.png" alt="Tip $5 on Ko-fi" height="32"></a>
</p>

---

## Install

1. Download the latest **Windows zip** from [Releases](https://github.com/HeadAroundIt/pasteflick/releases/latest).
2. Extract it.
3. Double-click **Install PasteFlick.bat**.

Copy to the clipboard works on its own. **Fling** and **PDF save** use a small Windows helper that Setup installs and starts with Windows. You do not install Python.

### Finish in the browser

Browsers will not silently install extensions. Setup opens a short guide, copies the folder path, and launches your Extensions page. Then:

1. Turn on **Developer mode**
2. Click **Load unpacked**
3. Paste the path and open that folder

Leave Developer mode on. Repeat in each Chromium browser you use. After that, updates come from GitHub on login.

Share the [latest release](https://github.com/HeadAroundIt/pasteflick/releases/latest) or a clone of this repo — not a working folder, and not `%LOCALAPPDATA%\PasteFlick`.

### Uninstall

`%LOCALAPPDATA%\PasteFlick\Uninstall.bat`

Then remove the extension from the browser if it is still listed.

---

## Privacy

Runs in your browser. Copied text stays on your device. Fling uses a local helper on your computer.
