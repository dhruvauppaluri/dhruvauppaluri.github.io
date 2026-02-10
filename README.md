# Electrical Engineering Portfolio

A single-page portfolio site for electrical engineering — circuits, embedded systems, PCB design — built for **GitHub Pages**.

## Live preview locally

Open `index.html` in a browser, or run a simple server:

```bash
# Python 3
python3 -m http.server 8000

# Then visit http://localhost:8000
```

## Deploy to GitHub Pages

1. **Create a new repo** on GitHub (e.g. `username.github.io` for a user site, or any repo name for a project site).

2. **Push this folder** to the repo:
   ```bash
   git init
   git add .
   git commit -m "Initial portfolio"
   git branch -M main
   git remote add origin https://github.com/dhruvauppaluri/dhruvauppaluri.github.io.git
   git push -u origin main
   ```

3. **Turn on GitHub Pages**:
   - Repo → **Settings** → **Pages**
   - **Source**: Deploy from a branch
   - **Branch**: `main` (or `master`), folder: **/ (root)**
   - Save

4. **View the site**: https://dhruvauppaluri.github.io

## Customize

- **About**: Edit the paragraph in the `#about` section in `index.html`.
- **Skills**: Change the four skill cards (icons are emoji; you can replace with SVGs).
- **Projects**: Replace the three project cards with your real projects and add real `href` values to "View details" (e.g. GitHub repo or a separate page).
- **Contact**: Update the email and the GitHub/LinkedIn URLs in the `#contact` section.

No build step required — plain HTML, CSS, and JS.
