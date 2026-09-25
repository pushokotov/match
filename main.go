package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"strings"
	"strconv"
	"syscall"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func main() {
	cfg := loadConfig()
	if cfg.TelegramToken == "" {
		log.Fatal("TELEGRAM_TOKEN is not set")
	}

	store := NewSessionStore(cfg)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	opts := []bot.Option{
		bot.WithWorkers(4),
		bot.WithDefaultHandler(defaultHandler(store)),
	}

	b, err := bot.New(cfg.TelegramToken, opts...)
	if err != nil {
		log.Fatalf("create telegram bot: %v", err)
	}

	registerHandlers(b, store)
	log.Println("Match Go bot started")
	b.Start(ctx)
}

func registerHandlers(b *bot.Bot, store *SessionStore) {
	b.RegisterHandler(bot.HandlerTypeMessageText, "/start", bot.MatchTypeCommandStartOnly, startHandler(store))
	b.RegisterHandler(bot.HandlerTypeMessageText, "Profile information", bot.MatchTypeExact, profileHandler(store))
	b.RegisterHandler(bot.HandlerTypeMessageText, "Run AutoSwipe", bot.MatchTypeExact, locationPromptHandler(store))
	b.RegisterHandler(bot.HandlerTypeMessageText, "Stop", bot.MatchTypeExact, stopHandler(store))
	b.RegisterHandler(bot.HandlerTypeMessageText, "Try again", bot.MatchTypeExact, tryAgainHandler(store))

	b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "phone_number_auth", bot.MatchTypeExact, phoneAuthHandler(store))
	b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "token_auth", bot.MatchTypeExact, tokenAuthHandler(store))
	b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "profile", bot.MatchTypeExact, profileHandler(store))
	b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "autoswipe", bot.MatchTypeExact, locationPromptHandler(store))
	b.RegisterHandler(bot.HandlerTypeCallbackQueryData, "stop", bot.MatchTypeExact, stopHandler(store))

	b.RegisterHandler(bot.HandlerTypeMessageText, "", bot.MatchTypeExact, textStateHandler(store))
}

func defaultHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		if update.Message == nil {
			return
		}
		textStateHandler(ctx, b, update)
	}
}

func startHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		if update.Message == nil {
			return
		}
		s := store.Get(update.Message.From.ID)
		s.mu.Lock()
		s.State = StateIdle
		s.Phone = ""
		s.mu.Unlock()

		sendStart(ctx, b, update.Message.Chat.ID, update.Message.From.FirstName)
	}
}

func phoneAuthHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		answerCallback(ctx, b, update)
		if update.CallbackQuery == nil || update.CallbackQuery.Message.Message == nil {
			return
		}
		s := store.Get(update.CallbackQuery.From.ID)
		s.mu.Lock()
		s.State = StatePhone
		s.mu.Unlock()
		sendText(ctx, b, update.CallbackQuery.Message.Message.Chat.ID, "Enter a phone number connected to your Tinder account.")
	}
}

func tokenAuthHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		answerCallback(ctx, b, update)
		if update.CallbackQuery == nil || update.CallbackQuery.Message == nil {
			return
		}
		s := store.Get(update.CallbackQuery.From.ID)
		s.mu.Lock()
		s.State = StateToken
		s.mu.Unlock()
		sendText(ctx, b, update.CallbackQuery.Message.Chat.ID, "Enter Tinder auth token:")
	}
}

func profileHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		chatID, userID, ok := updateChatUser(update)
		if !ok {
			return
		}
		if update.CallbackQuery != nil {
			answerCallback(ctx, b, update)
		}

		s := store.Get(userID)
		s.mu.Lock()
		if s.Client == nil || !s.Client.hasToken() {
			s.mu.Unlock()
			sendText(ctx, b, chatID, "You are not authorized yet.")
			return
		}
		s.mu.Unlock()

		s.mu.Lock()
		client := s.Client
		s.mu.Unlock()

		profile, err := client.Profile(ctx)
		if err != nil {
			sendText(ctx, b, chatID, "Failed to load Tinder profile: "+err.Error())
			return
		}
		nearest, _ := client.Recommendations(ctx)
		matches, _ := client.MatchesCount(ctx, false)
		newMatches, _ := client.MatchesCount(ctx, true)

		text := "Hello, " + profile.Name + ".\n" +
			"Your current location is: " + profile.Country + ", " + profile.City + "\n" +
			"New users around: " + itoa(len(nearest)) + "\n" +
			"Common number of matches: " + itoa(matches) + "\n" +
			"Number of new matches: " + itoa(newMatches)

		sendMenu(ctx, b, chatID, text)
	}
}

func locationPromptHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		chatID, userID, ok := updateChatUser(update)
		if !ok {
			return
		}
		if update.CallbackQuery != nil {
			answerCallback(ctx, b, update)
		}

		s := store.Get(userID)
		s.mu.Lock()
		if !s.Client.hasToken() {
			s.mu.Unlock()
			sendText(ctx, b, chatID, "Authorize first.")
			return
		}
		s.State = StateLocation
		s.mu.Unlock()

		sendText(ctx, b, chatID, "Enter city or cities separated by comma:")
	}
}

func stopHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		chatID, userID, ok := updateChatUser(update)
		if !ok {
			return
		}
		if update.CallbackQuery != nil {
			answerCallback(ctx, b, update)
		}
		s := store.Get(userID)
		s.mu.Lock()
		s.State = StateIdle
		s.mu.Unlock()
		sendText(ctx, b, chatID, "Bot has been stopped.")
	}
}

func tryAgainHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		if update.Message == nil {
			return
		}
		s := store.Get(update.Message.From.ID)
		s.mu.Lock()
		s.State = StatePhone
		s.mu.Unlock()
		sendText(ctx, b, update.Message.Chat.ID, "Enter your phone number again:")
	}
}

func textStateHandler(store *SessionStore) bot.HandlerFunc {
	return func(ctx context.Context, b *bot.Bot, update *models.Update) {
		if update.Message == nil || strings.TrimSpace(update.Message.Text) == "" {
			return
		}

		userID := update.Message.From.ID
		chatID := update.Message.Chat.ID
		s := store.Get(userID)

		s.mu.Lock()
		state := s.State
		s.mu.Unlock()

		switch state {
		case StatePhone:
			handlePhone(ctx, b, s, chatID, update.Message.Text)
		case StateCode:
			handleCode(ctx, b, s, chatID, update.Message.Text)
		case StateToken:
			handleToken(ctx, b, s, chatID, update.Message.Text)
		case StateLocation:
			handleLocation(ctx, b, s, chatID, update.Message.Text)
		default:
			sendText(ctx, b, chatID, "Use the buttons below or /start.")
		}
	}
}

func handlePhone(ctx context.Context, b *bot.Bot, s *Session, chatID int64, phone string) {
	phone = strings.TrimSpace(phone)
	if len(phone) < 7 {
		sendText(ctx, b, chatID, "Please enter a valid phone number.")
		return
	}

	s.mu.Lock()
	s.Phone = phone
	s.mu.Unlock()

	if err := s.Client.AuthRequestCode(ctx, phone); err != nil {
		sendText(ctx, b, chatID, "Could not request SMS code: "+err.Error())
		return
	}

	s.mu.Lock()
	s.State = StateCode
	s.mu.Unlock()
	sendText(ctx, b, chatID, "Enter the 6-digit code sent to "+phone+".")
}

func handleCode(ctx context.Context, b *bot.Bot, s *Session, chatID int64, code string) {
	code = strings.TrimSpace(code)
	if len(code) != 6 || !allDigits(code) {
		sendText(ctx, b, chatID, "Please enter a valid 6-digit code.")
		return
	}

	s.mu.Lock()
	phone := s.Phone
	s.mu.Unlock()

	if err := s.Client.AuthWithCode(ctx, phone, code); err != nil {
		sendText(ctx, b, chatID, "Authorization failed. Try again.")
		s.mu.Lock()
		s.State = StatePhone
		s.mu.Unlock()
		return
	}

	s.mu.Lock()
	s.State = StateIdle
	s.mu.Unlock()
	sendMenu(ctx, b, chatID, "Authorization complete.")
}

func handleToken(ctx context.Context, b *bot.Bot, s *Session, chatID int64, token string) {
	token = strings.TrimSpace(token)
	if token == "" {
		sendText(ctx, b, chatID, "Token cannot be empty.")
		return
	}

	s.Client.SetToken(token)
	s.mu.Lock()
	s.State = StateIdle
	s.mu.Unlock()
	sendMenu(ctx, b, chatID, "Authorization complete.")
}

func handleLocation(ctx context.Context, b *bot.Bot, s *Session, chatID int64, input string) {
	cities := splitCities(input)
	if len(cities) == 0 {
		sendText(ctx, b, chatID, "Enter at least one city.")
		return
	}

	s.mu.Lock()
	if s.State == StateProcessing {
		s.mu.Unlock()
		sendText(ctx, b, chatID, "Autoswipe is already running.")
		return
	}
	s.State = StateProcessing
	client := s.Client
	s.mu.Unlock()

	go func() {
		before, _ := client.MatchesCount(ctx, true)
		totalLiked := 0

		for _, city := range cities {
			sendText(ctx, b, chatID, "Swiping in "+city+"...")
			liked, err := client.AutoSwipe(ctx, city, s.AlreadyLiked)
			if err != nil {
				sendText(ctx, b, chatID, "Error in "+city+": "+err.Error())
				continue
			}
			totalLiked += liked
			sendText(ctx, b, chatID, "Liked "+itoa(liked)+" profiles in "+city+".")
		}

		after, _ := client.MatchesCount(ctx, true)
		sendText(ctx, b, chatID, "AutoSwipe finished.\nLikes sent: "+itoa(totalLiked)+"\nNew matches: "+itoa(after-before))

		s.mu.Lock()
		s.State = StateIdle
		s.mu.Unlock()
	}()
}

func updateChatUser(update *models.Update) (int64, int64, bool) {
	if update.Message != nil {
		return update.Message.Chat.ID, update.Message.From.ID, true
	}
	if update.CallbackQuery != nil && update.CallbackQuery.Message.Message != nil {
		return update.CallbackQuery.Message.Message.Chat.ID, update.CallbackQuery.From.ID, true
	}
	return 0, 0, false
}

func answerCallback(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.CallbackQuery == nil {
		return
	}
	_, _ = b.AnswerCallbackQuery(ctx, &bot.AnswerCallbackQueryParams{
		CallbackQueryID: update.CallbackQuery.ID,
	})
}

func sendStart(ctx context.Context, b *bot.Bot, chatID int64, firstName string) {
	text := "Hi, " + firstName + "!\nWelcome to Match Go."
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text: text,
		ReplyMarkup: inlineMenu([][]button{
			{{"Sign in with phone number", "phone_number_auth"}},
			{{"Sign in with token", "token_auth"}},
		}),
	})
}

func sendMenu(ctx context.Context, b *bot.Bot, chatID int64, text string) {
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text: text,
		ReplyMarkup: inlineMenu([][]button{
			{{"Profile information", "profile"}},
			{{"Run AutoSwipe", "autoswipe"}},
			{{"Stop", "stop"}},
		}),
	})
}

func sendText(ctx context.Context, b *bot.Bot, chatID int64, text string) {
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{ChatID: chatID, Text: text})
}

type button struct {
	text string
	data string
}

func inlineMenu(rows [][]button) *models.InlineKeyboardMarkup {
	result := &models.InlineKeyboardMarkup{}
	for _, row := range rows {
		items := make([]models.InlineKeyboardButton, 0, len(row))
		for _, item := range row {
			items = append(items, models.InlineKeyboardButton{
				Text: item.text,
				CallbackData: item.data,
			})
		}
		result.InlineKeyboard = append(result.InlineKeyboard, items)
	}
	return result
}

func splitCities(input string) []string {
	raw := strings.Split(input, ",")
	result := make([]string, 0, len(raw))
	for _, city := range raw {
		city = strings.TrimSpace(city)
		if city != "" {
			result = append(result, city)
		}
	}
	return result
}

func allDigits(s string) bool {
	for _, r := range s {
		if r < '0' || r > '9' {
			return false
		}
	}
	return true
}

func itoa(n int) string {
	return strconv.Itoa(n)
}

