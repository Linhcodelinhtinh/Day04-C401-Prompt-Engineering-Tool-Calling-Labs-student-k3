---
name: meme_search
track: team
kind: live_api
provider: Giphy
requires_env: [GIPHY_API_KEY]
inputs: [query, limit, rating]
outputs: [items]
side_effect: false
---
# meme_search

Searches Giphy for a GIF/meme matching `query`. Call it when the user
explicitly asks for something funny/a meme/a GIF, or proactively when another
tool's result surfaces a phrase/moment that is itself a well-known meme or
viral joke (not just a mention of a public figure). Prefer `query` values
built around well-known, recognizable meme subjects/formats (e.g. Ronaldo
Siuu, Donald Trump, Elon Musk, Drake, distracted boyfriend) over vague
descriptions — they return funnier, more recognizable results. Do not attach
a meme to plain factual content that has nothing meme-worthy in it.
`rating` defaults to `g` to keep results classroom-safe.
