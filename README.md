<p align="center">
  <img src="extension/icons/icon-master.png" width="96" height="96" alt="PasteFlick">
</p>

<h1 align="center">PasteFlick</h1>

<p align="center">
  Copy a ChatGPT highlight or the visible thread, then flick it into the last app.
</p>

**Windows only.** Not affiliated with OpenAI.

Repo: [github.com/HeadAroundIt/pasteflick](https://github.com/HeadAroundIt/pasteflick)

One extension for **Brave, Chrome, Edge, Chromium, and Arc**. ChatGPT only.

PasteFlick copies what is on the page. If ChatGPT has not rendered a turn yet, that turn is not in the copy.

---

## What you get

One chip under the chat title. Highlight a passage, or take the visible thread — then **Copy**, **Save**, or **Fling** it into the last app you were using. ChatGPT’s own buttons stay where they are.

Pin any message. **Copy from PasteFlick** starts at that pin, so you can take the rest of the conversation without dragging a selection.

The toolbar popup is there when you want it:

- **Copy selection** — the highlight you made
- **Copy thread** — the conversation currently on the page
- **Copy from PasteFlick** — from your pin onward

Choose where the text goes:

- **Clipboard** — ready to paste when you are
- **Fling** — into the last app you were in (Windows helper)
- **File** — Markdown or PDF, in a folder you pick

The first time you copy, allow clipboard access if ChatGPT or the browser asks.

---

## Install

1. Download **PasteFlick-&lt;version&gt;-windows.zip** from the [latest official release](https://github.com/HeadAroundIt/pasteflick/releases/latest).
2. Extract the zip.
3. Double-click **Install PasteFlick.bat**.

Clipboard copying works without extra software. **Auto-paste and PDF export** use a bundled Windows helper that Setup copies and starts; you do not install Python. The helper also starts with Windows so the first Fling click is not an install step.

### Finish in the browser

The installer copies the extension into a local folder, opens a short guide, and launches your Extensions page. Then:

1. Turn on **Developer mode**
2. Click **Load unpacked**
3. Paste the folder path (already on the clipboard) and open it

Leave Developer mode on. Chrome turns unpacked extensions off if you switch it off.

Browsers block fully silent extension installs, so Load unpacked is the last step. Repeat it in each Chromium browser you use.

After that, updates come from GitHub (`main`) on login. You should not need Load unpacked again. Official versioned downloads remain available on the [Releases page](https://github.com/HeadAroundIt/pasteflick/releases).

Do not zip this working folder or copy `%LOCALAPPDATA%\PasteFlick`. Those can include personal notes, and a local `dev-hold` file pauses GitHub updates. Send the [latest release](https://github.com/HeadAroundIt/pasteflick/releases/latest) or a clone of the GitHub repo.

### Uninstall

`%LOCALAPPDATA%\PasteFlick\Uninstall.bat`

Then remove the extension from your browser’s Extensions page if it is still listed.

---

## Privacy

Runs in your browser. Copied text stays on your device. Auto-paste uses a local helper on your computer.
