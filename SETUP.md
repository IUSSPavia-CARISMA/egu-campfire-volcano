# Volcano Campfire — Setup Guide
EGU GMPV-NH Campfire · "Volcanoes Across Disciplines"

---

## Files in this repo

| File | Purpose |
|---|---|
| `prepare_data.py` | Run once to generate `volcanoes.json` from GVP |
| `index.html` | The interactive map app |
| `volcanoes.json` | Generated data file (commit this after running the script) |
| `SETUP.md` | This file |

---

## Step 1 — Firebase project (5 min)

1. Go to [console.firebase.google.com](https://console.firebase.google.com)
2. **Add project** → give it a name (e.g. `egu-campfire`) → Continue → Create project
3. In the left sidebar: **Build → Realtime Database → Create database**
   - Choose a region close to Vienna (europe-west1)
   - Start in **test mode** (allows public read/write — fine for a 1-hour event)
4. In the left sidebar: **Project Overview (⚙ gear icon) → Project settings → Your apps**
   - Click the web icon `</>`
   - Register app (name it anything) → you'll see a `firebaseConfig` object
5. Copy the config values into `index.html` at the top of the `<script>` block:

```javascript
const FIREBASE_CONFIG = {
  apiKey:            "AIzaSy...",
  authDomain:        "egu-campfire.firebaseapp.com",
  databaseURL:       "https://egu-campfire-default-rtdb.europe-west1.firebasedatabase.app",
  projectId:         "egu-campfire",
  storageBucket:     "egu-campfire.appspot.com",
  messagingSenderId: "12345...",
  appId:             "1:12345...:web:abcdef..."
};
```

---

## Step 2 — Generate volcanoes.json (5 min)

Run this once on your laptop, a day or two before the event so eruption data is current.

```bash
pip install requests beautifulsoup4 lxml
python prepare_data.py
```

Expected output:
```
Fetching volcano list from GVP WFS GeoServer…
  → 1402 volcanoes loaded  (8 skipped: no coordinates).
Fetching current eruptions from GVP…
  → 43 currently erupting volcanoes identified.
  → 43 volcanoes flagged as currently erupting.

✓ Saved volcanoes.json
  Total volcanoes     : 1402
  Currently erupting  : 43
  Historically active : 1198
  File size           : 680 KB
```

---

## Step 3 — GitHub repository & Pages (5 min)

```bash
git init volcano-campfire
cd volcano-campfire
# copy index.html and volcanoes.json here
git add index.html volcanoes.json
git commit -m "initial deploy"
gh repo create volcano-campfire --public --source=. --push
```

Then enable GitHub Pages:
- Repository → **Settings → Pages**
- Source: **Deploy from branch** → `main` → `/ (root)` → Save
- Your URL will be: `https://YOUR_USERNAME.github.io/volcano-campfire`
- It takes ~1 minute to go live

---

## Step 4 — QR code

Generate a QR code pointing to your GitHub Pages URL. Free tools:
- [qr-code-generator.com](https://www.qr-code-generator.com)
- [goqr.me](https://goqr.me)

Display the QR code on the projected screen at the start of the session.

---

## On the day — how it works

| What the audience sees | What it means |
|---|---|
| 🔴 Red pulsing dot | Currently erupting volcano |
| 🟠 Orange dot | Historically active (Holocene) |
| 🟡 Yellow dot | Fumarolic activity only |
| 🟢 Green dot | Hydrothermal activity only |
| ⚫ Grey dot | Uncertain activity |
| Blue ring | At least one person in the room visited this volcano |

**Interaction flow:**
1. Show QR code → audience scans and opens the map on their phones
2. They tap any volcano they've worked on or visited
3. The projected screen (which is also just the URL open in a browser) updates in real time
4. Blue rings appear on the projected map as people mark their volcanoes
5. Counter in the top-right grows — good moment to comment on the collective field experience in the room

---

## Suggested facilitation

**Opening (before talks):**
> "Before we start — scan the QR code, open the map, and tap every volcano you've
> worked on or visited. You have 3 minutes."
>
> [let it fill up, then comment on what you see — e.g. clustering in certain regions,
> surprising remote volcanoes, how many people have been to the same volcano]

**During talks:**
Keep the map visible on a second screen or return to it between speakers.
Petrologists will have marked different volcanoes from hazard modellers — makes the disciplinary divide visible.

**Closing:**
Ask the room: "Which volcano on this map would most benefit from all three disciplines working together?"

---

## Firebase cleanup after the event

In the Firebase console → Realtime Database → Rules, change to:
```json
{
  "rules": {
    ".read": false,
    ".write": false
  }
}
```
This prevents any further writes after the event. You can also delete the project entirely.

---

## Data source

Volcano data: Smithsonian Institution Global Volcanism Program, Volcanoes of the World (VOTW) database.
Venzke, E (ed.), 2013–present. Smithsonian Institution. https://doi.org/10.5479/si.GVP.VOTW5-2023.5.2

Current eruption status: Smithsonian / USGS Weekly Volcanic Activity Report (updated weekly).
