package main

import "sync"

type SessionState string

const (
	StateIdle       SessionState = "idle"
	StatePhone      SessionState = "phone"
	StateCode       SessionState = "code"
	StateToken      SessionState = "token"
	StateLocation   SessionState = "location"
	StateProcessing SessionState = "processing"
)

type Session struct {
	mu           sync.Mutex
	Client       *TinderClient
	State        SessionState
	Phone        string
	AlreadyLiked map[string]struct{}
}

type SessionStore struct {
	mu       sync.Mutex
	sessions map[int64]*Session
	cfg      Config
}

func NewSessionStore(cfg Config) *SessionStore {
	return &SessionStore{sessions: make(map[int64]*Session), cfg: cfg}
}

func (s *SessionStore) Get(userID int64) *Session {
	s.mu.Lock()
	defer s.mu.Unlock()

	session, ok := s.sessions[userID]
	if !ok {
		session = &Session{
			Client:       NewTinderClient(s.cfg),
			State:        StateIdle,
			AlreadyLiked: make(map[string]struct{}),
		}
		s.sessions[userID] = session
	}
	return session
}

func (s *SessionStore) Reset(userID int64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.sessions, userID)
}
