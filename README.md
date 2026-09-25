# Match — Go rewrite

This branch contains the first Go rewrite of the original Telegram Tinder-style bot.

## Stack

- Go 1.27.1
- github.com/go-telegram/bot
- Go standard library for HTTP, JSON, concurrency and geocoding

## Environment

Required:

- `TELEGRAM_TOKEN`

Optional:

- `TINDER_API_URL` — defaults to `https://api.gotinder.com`
- `TINDER_LOCALE` — defaults to `ru`
- `TINDER_USER_AGENT`

## Run locally

```bash
go mod tidy
go run .
```

## Build

```bash
go build -o match .
./match
```

## Current architecture

Each Telegram user has an isolated session and Tinder client. Authentication tokens are not stored in global process-wide HTTP headers.

The first rewrite preserves the original flow:

1. `/start`
2. Tinder phone authentication or token authentication
3. Profile information
4. City selection
5. Tinder location change
6. Recommendation loading
7. Like profiles with at least two photos
8. Pass profiles with fewer than two photos
9. Match count before and after AutoSwipe

The Python implementation remains on `main` until this branch is tested.

## Important

The Tinder API is an external/private API. The Go rewrite preserves the endpoints and authentication protocol used by the original project; those endpoints may have changed since the original bot was written. Test authentication and one controlled AutoSwipe before considering the rewrite production-ready.
