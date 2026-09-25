package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/rand/v2"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"
)

type TinderClient struct {
	baseURL    string
	locale     string
	userAgent  string
	token      string
	httpClient *http.Client
}

type TinderProfile struct {
	City    string
	Country string
	Name    string
	Purchases bool
}

type Recommendation struct {
	UserID  string
	SNumber int64
	Photos  []string
	PhotoID string
}

type geoResult struct {
	Lat          string   `json:"lat"`
	Lon          string   `json:"lon"`
	BoundingBox  []string `json:"boundingbox"`
}

func NewTinderClient(cfg Config) *TinderClient {
	return &TinderClient{
		baseURL:    strings.TrimRight(cfg.TinderAPIURL, "/"),
		locale:     cfg.Locale,
		userAgent:  cfg.UserAgent,
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
}

func (c *TinderClient) SetToken(token string) {
	c.token = strings.TrimSpace(token)
}

func (c *TinderClient) hasToken() bool {
	return c.token != ""
}

func (c *TinderClient) headers(req *http.Request) {
	req.Header.Set("X-Auth-Token", c.token)
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", c.userAgent)
	req.Header.Set("X-Supported-Image-Formats", "webp,jpeg")
	req.Header.Set("Persistent-Device-Id", "match-go")
	req.Header.Set("Platform", "web")
}

func (c *TinderClient) do(ctx context.Context, method, rawURL string, body io.Reader, contentType string) (*http.Response, error) {
	req, err := http.NewRequestWithContext(ctx, method, rawURL, body)
	if err != nil {
		return nil, err
	}
	c.headers(req)
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		defer resp.Body.Close()
		data, _ := io.ReadAll(io.LimitReader(resp.Body, 4096))
		return nil, fmt.Errorf("tinder API %s: %s: %s", method, resp.Status, strings.TrimSpace(string(data)))
	}
	return resp, nil
}

func (c *TinderClient) getJSON(ctx context.Context, path string, dst any) error {
	resp, err := c.do(ctx, http.MethodGet, c.baseURL+path, nil, "")
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	return json.NewDecoder(resp.Body).Decode(dst)
}

func (c *TinderClient) postRaw(ctx context.Context, path, body string) (*http.Response, error) {
	return c.do(ctx, http.MethodPost, c.baseURL+path, strings.NewReader(body), "application/x-google-protobuf")
}

func (c *TinderClient) AuthRequestCode(ctx context.Context, phone string) error {
	phone = strings.NewReplacer("+", "", " ", "", "-", "(", ")", "").Replace(phone)
	body := fmt.Sprintf("\n\x0e\n\x0c%s", phone)
	resp, err := c.postRaw(ctx, "/v3/auth/login?locale="+url.QueryEscape(c.locale), body)
	if err != nil {
		return err
	}
	resp.Body.Close()
	return nil
}

func (c *TinderClient) AuthWithCode(ctx context.Context, phone, code string) error {
	phone = strings.NewReplacer("+", "", " ", "", "-", "(", ")", "").Replace(phone)
	phoneData := fmt.Sprintf("\n\x0e\n\x0c%s", phone)
	body := fmt.Sprintf("\x12\x18%s\x12\x06%s", phoneData, code)

	resp, err := c.postRaw(ctx, "/v3/auth/login?locale="+url.QueryEscape(c.locale), body)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	token, err := extractAuthToken(string(data))
	if err != nil {
		return err
	}
	c.token = token
	return nil
}

func extractAuthToken(body string) (string, error) {
	re := regexp.MustCompile("\x12\$([^"]*)"\x18")
	m := re.FindStringSubmatch(body)
	if len(m) != 2 {
		return "", errors.New("could not extract Tinder auth token from response")
	}
	return m[1], nil
}

func (c *TinderClient) Profile(ctx context.Context) (TinderProfile, error) {
	path := "/v2/profile?locale=" + url.QueryEscape(c.locale) +
		"&include=account%2Cboost%2Ccontact_cards%2Cemail_settings%2Cinstagram%2Clikes%2Cnotifications%2Cplus_control%2Cproducts%2Cpurchase%2Creadreceipts%2Cswipenote%2Cspotify%2Csuper_likes%2Ctinder_u%2Ctravel%2Ctutorials%2Cuser"

	var root map[string]any
	if err := c.getJSON(ctx, path, &root); err != nil {
		return TinderProfile{}, err
	}

	data, _ := root["data"].(map[string]any)
	user, _ := data["user"].(map[string]any)
	name, _ := user["name"].(string)

	city := "Город не определен"
	country := ""

	if pos, ok := user["pos_info"].(map[string]any); ok {
		if state, ok := pos["state"].(map[string]any); ok {
			city, _ = state["name"].(string)
		} else if cityObj, ok := pos["city"].(map[string]any); ok {
			city, _ = cityObj["name"].(string)
		}
		if countryObj, ok := pos["country"].(map[string]any); ok {
			country, _ = countryObj["name"].(string)
		}
	}

	purchases := false
	if purchase, ok := data["purchase"].(map[string]any); ok {
		if list, ok := purchase["purchases"].([]any); ok {
			purchases = len(list) > 0
		}
	}

	return TinderProfile{Name:name, City:city, Country:country, Purchases:purchases}, nil
}

func (c *TinderClient) MatchesCount(ctx context.Context, onlyNew bool) (int, error) {
	var total int
	var pageToken string

	for {
		path := "/v2/matches?locale=" + url.QueryEscape(c.locale) + "&count=100&is_tinder_u=false"
		if pageToken != "" {
			path += "&page_token=" + url.QueryEscape(pageToken)
		}

		var root map[string]any
		if err := c.getJSON(ctx, path, &root); err != nil {
			return 0, err
		}

		data, _ := root["data"].(map[string]any)
		matches, _ := data["matches"].([]any)

		for _, raw := range matches {
			if !onlyNew {
				total++
				continue
			}
			match, _ := raw.(map[string]any)
			seen, _ := match["seen"].(map[string]any)
			if v, ok := seen["match_seen"].(bool); ok && !v {
				total++
			}
		}

		next, _ := data["next_page_token"].(string)
		if next == "" {
			return total, nil
		}
		pageToken = next
	}
}

func (c *TinderClient) Recommendations(ctx context.Context) ([]Recommendation, error) {
	var root struct {
		Data struct {
			Results []struct {
				User struct {
					ID     string `json:"_id"`
					Photos []struct {
						ID string `json:"id"`
					} `json:"photos"`
				} `json:"user"`
				SNumber int64 `json:"s_number"`
			} `json:"results"`
		} `json:"data"`
	}

	if err := c.getJSON(ctx, "/v2/recs/core?locale="+url.QueryEscape(c.locale), &root); err != nil {
		return nil, err
	}

	result := make([]Recommendation, 0, len(root.Data.Results))
	for _, item := range root.Data.Results {
		photos := make([]string, 0, len(item.User.Photos))
		for _, p := range item.User.Photos {
			photos = append(photos, p.ID)
		}
		if item.User.ID == "" {
			continue
		}
		photoID := ""
		if len(photos) > 0 {
			photoID = photos[rand.IntN(len(photos))]
		}
		result = append(result, Recommendation{
			UserID:item.User.ID,
			SNumber:item.SNumber,
			Photos:photos,
			PhotoID:photoID,
		})
	}
	return result, nil
}

func (c *TinderClient) swipe(ctx context.Context, rec Recommendation, like bool) error {
	if like {
		path := "/like/" + url.PathEscape(rec.UserID) + "?locale=" + url.QueryEscape(c.locale)
		resp, err := c.do(ctx, http.MethodPost, c.baseURL+path, nil, "")
		if err != nil {
			return err
		}
		resp.Body.Close()
		return nil
	}

	path := "/pass/" + url.PathEscape(rec.UserID) +
		"?locale=" + url.QueryEscape(c.locale) +
		"&s_number=" + strconv.FormatInt(rec.SNumber, 10)
	resp, err := c.do(ctx, http.MethodGet, c.baseURL+path, nil, "")
	if err != nil {
		return err
	}
	resp.Body.Close()
	return nil
}

func (c *TinderClient) ChangeLocation(ctx context.Context, city string) error {
	geo, err := geocode(ctx, city)
	if err != nil {
		return err
	}

	lat, lon := geo.Lat, geo.Lon
	if len(geo.BoundingBox) == 4 {
		minLat, _ := strconv.ParseFloat(geo.BoundingBox[0], 64)
		maxLat, _ := strconv.ParseFloat(geo.BoundingBox[1], 64)
		minLon, _ := strconv.ParseFloat(geo.BoundingBox[2], 64)
		maxLon, _ := strconv.ParseFloat(geo.BoundingBox[3], 64)
		if maxLat < minLat {
			minLat, maxLat = maxLat, minLat
		}
		if maxLon < minLon {
			minLon, maxLon = maxLon, minLon
		}
		lat = strconv.FormatFloat(minLat+rand.Float64()*(maxLat-minLat), 'f', 7, 64)
		lon = strconv.FormatFloat(minLon+rand.Float64()*(maxLon-minLon), 'f', 7, 64)
	}

	payload := fmt.Sprintf(`{"lat":%s,"lon":%s,"force_fetch_resources":true}`, lat, lon)
	resp, err := c.do(ctx, http.MethodPost,
		c.baseURL+"/v2/meta?locale="+url.QueryEscape(c.locale),
		strings.NewReader(payload), "application/json")
	if err != nil {
		return err
	}
	resp.Body.Close()
	return nil
}

func geocode(ctx context.Context, city string) (geoResult, error) {
	q := url.Values{}
	q.Set("q", city)
	q.Set("format", "json")
	q.Set("limit", "1")

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://nominatim.openstreetmap.org/search?"+q.Encode(), nil)
	if err != nil {
		return geoResult{}, err
	}
	req.Header.Set("User-Agent", "match-go/1.0")

	client := &http.Client{Timeout:15*time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return geoResult{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return geoResult{}, fmt.Errorf("geocoder returned %s", resp.Status)
	}

	var results []geoResult
	if err := json.NewDecoder(resp.Body).Decode(&results); err != nil {
		return geoResult{}, err
	}
	if len(results) == 0 {
		return geoResult{}, fmt.Errorf("city %q was not found", city)
	}
	return results[0], nil
}

func (c *TinderClient) AutoSwipe(ctx context.Context, city string, alreadyLiked map[string]struct{}) (int, error) {
	if err := c.ChangeLocation(ctx, city); err != nil {
		return 0, err
	}

	results, err := c.Recommendations(ctx)
	if err != nil {
		return 0, err
	}

	liked := 0
	for _, rec := range results {
		if _, exists := alreadyLiked[rec.UserID]; exists {
			continue
		}

		shouldLike := len(rec.Photos) >= 2
		if err := c.swipe(ctx, rec, shouldLike); err != nil {
			return liked, err
		}

		if shouldLike {
			alreadyLiked[rec.UserID] = struct{}{}
			liked++
		}

		delay := time.Duration(rand.IntN(6)) * time.Second
		select {
		case <-ctx.Done():
			return liked, ctx.Err()
		case <-time.After(delay):
		}
	}

	return liked, nil
}
