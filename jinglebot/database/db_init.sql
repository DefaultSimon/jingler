CREATE TABLE IF NOT EXISTS guild_settings (
    /**
      Guild ID
     */
    id INTEGER PRIMARY KEY,
    /**
      Jingle modes:
       0: disabled
       1: single
       2: random
     */
    jingle_mode INTEGER DEFAULT 2 NOT NULL,
    /**
      Personal theme song modes:
       0: ignore theme songs
       1: allow (play) theme songs if a user has one
     */
    theme_song_mode INTEGER DEFAULT 1 NOT NULL,
    /**
      ID of the jingle that was set as the default.
     */
    default_jingle_id TEXT
);

CREATE TABLE IF NOT EXISTS user_settings (
    /**
      User ID
     */
     id INTEGER PRIMARY KEY,
     /**
       ID of the jingle that was set as that user's theme song.
      */
     theme_song_jingle_id TEXT
);
