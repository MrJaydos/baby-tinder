# Baby Tinder

A Tinder-style baby name app for expecting parents. Both partners swipe left or right on names independently — when you both like the same name, it's a match!

---

## Features

- Swipe right to like a name, left to pass
- Instant match notification when both partners like the same name
- Filter names by gender (boy / girl / neutral), origin, and style/type
- Keyboard shortcuts: `→` or `L` to like, `←` or `H` to pass
- View all your matches in one place
- Couple system — each partner has their own account, linked by a shared code

---

## Getting Started

### 1. Create an account

Go to **Sign Up** and register with your name, email, and password. There are no pre-seeded accounts — everyone registers fresh.

### 2. Set up your couple

After signing up you'll be taken to the **Couple Setup** page. One partner clicks **Create Couple** and gets a 6-character code. The other partner goes to Couple Setup and enters that code to join.

You can share your couple code at any time from the **Account** page.

### 3. Start swiping

Head to **Swipe** and work through the names. Use the filters on the left to narrow down by:

- **Gender** — Boy, Girl, or Neutral
- **Origin** — e.g. English, Hebrew, French
- **Style / Type** — e.g. Classic, Modern, Nature

Click the **✓ heart** button (or press `→`) to like a name, and the **✗** button (or press `←`) to pass.

### 4. See your matches

When both you and your partner like the same name a match popup appears instantly. All your matches are saved and viewable on the **Matches** page.

---

## Running Locally

```bash
pip install -r requirements.txt
python main.py
```

The app runs at `http://localhost:5000`. On first startup it automatically imports the baby names from `names.db`.

---

## Deploying with Coolify

The repo includes a `Dockerfile` and `docker-compose.yml`. In Coolify:

1. Add a new service and point it at this repository.
2. Coolify will detect the `Dockerfile` automatically.
3. Set the following environment variables in Coolify's UI:

| Variable | Description |
|---|---|
| `SECRET_KEY` | A long random string for session security |
| `DATABASE_URL` | Leave blank to use SQLite (default), or set a PostgreSQL URL |

4. Add a persistent volume mounted at `/data` so the database survives restarts.
5. Deploy — the app will be live on the port you configure (default `5000`).

For PostgreSQL, set `DATABASE_URL` to:
```
postgresql://user:password@host:5432/babytinder
```
