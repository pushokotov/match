package main

import "os"

type Config struct {
	TelegramToken string
	TinderAPIURL  string
	Locale        string
	UserAgent     string
}

func loadConfig() Config {
	apiURL := os.Getenv("TINDER_API_URL")
	if apiURL == "" {
		apiURL = "https://api.gotinder.com"
	}

	locale := os.Getenv("TINDER_LOCALE")
	if locale == "" {
		locale = "ru"
	}

	userAgent := os.Getenv("TINDER_USER_AGENT")
	if userAgent == "" {
		userAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/150.0 Safari/537.36"
	}

	return Config{
		TelegramToken: os.Getenv("TELEGRAM_TOKEN"),
		TinderAPIURL:  apiURL,
		Locale:        locale,
		UserAgent:     userAgent,
	}
}
