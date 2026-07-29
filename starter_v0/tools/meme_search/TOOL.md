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

Searches Giphy for a GIF/meme matching `query`. Only call this when the user
explicitly asks for something funny/a meme/a GIF — never attach it to a
serious research digest unasked. `rating` defaults to `g` to keep results
classroom-safe.
