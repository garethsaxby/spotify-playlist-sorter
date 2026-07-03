# Contract: External APIs used

The exact external calls the tool depends on. These are the integration boundary; each
response is validated into typed models before use (Constitution V).

## ReccoBeats (no auth)

Base: `https://api.reccobeats.com/v1`

### Get audio features (batch)
`GET /audio-features?ids={id1,id2,...}` — up to **40** Spotify track IDs per request.

Response (verified live 2026-07-03):
```json
{ "content": [
  { "id": "<reccobeats-uuid>",
    "href": "https://open.spotify.com/track/003vvx7Niy0yvhvHt4a68B",
    "isrc": "USIR20400274",
    "key": 1, "mode": 1, "tempo": 148.033,
    "energy": 0.911, "danceability": 0.352, "valence": 0.236,
    "acousticness": 0.00121, "instrumentalness": 0.0, "liveness": 0.0995,
    "loudness": -5.23, "speechiness": 0.0747 }
] }
```
Contract facts:
- Fields used: `href` (→ Spotify ID), `key` (0–11), `mode` (0/1), `tempo` (BPM).
- Results **may be fewer than requested** and in **any order** → map by `href`.
- Unknown IDs → simply absent; a request with no matches → `{"content": []}`, HTTP 200.
- Missing/invalid features for a track → that track is **unsortable** (FR-012/FR-018).
- 429 → honour `Retry-After`.

## Spotify Web API (OAuth Authorization Code + PKCE)

Base: `https://api.spotify.com/v1`. Scopes: `playlist-read-private`,
`playlist-read-collaborative`, `playlist-modify-public`, `playlist-modify-private`.

| Purpose | Call | Notes |
|---------|------|-------|
| Current user | `GET /me` | `id` used for ownership check + playlist creation |
| Playlist meta | `GET /playlists/{id}` | `name`, `owner.id` (ownership → FR-003) |
| Playlist tracks | `GET /playlists/{id}/tracks?limit=100&offset=…` | paginate via `next` until exhausted (FR-004) |
| Create playlist | `POST /users/{user_id}/playlists` | body: `name`, `public`, `description`; returns new `id`, `external_urls` |

**New playlist defaults**: created **private** (`public: false`) — safer for a personal
library copy (a `--public` flag may be offered); name = `"{source playlist name} (Camelot
sorted)"`, overridable via `--name`.
| Add tracks | `POST /playlists/{id}/tracks` | body: `uris` (≤100 per call); call sequentially to preserve order (FR-009) |

Contract facts:
- Ownership: proceed only if `playlist.owner.id == me.id` (else exit 4).
- Only the **new** playlist is written; the source is never modified (FR-009).
- 429 → honour `Retry-After` and retry.
- Auth: access token obtained via PKCE; refresh token cached to a `0600` config file; the
  `client_id` is a non-secret registered app credential (user-provided).
