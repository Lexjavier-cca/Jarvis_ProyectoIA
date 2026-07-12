import sqlite3
import json
import os
import re

DB_PATH = os.path.join(os.path.dirname(__file__), "jarvis.db")

class DBManager:
    def __init__(self):
        self.init_db()
        self.init_songs_table()

    def init_db(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_input TEXT,
            bot_response TEXT,
            intent TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            ip TEXT,
            port INTEGER,
            type TEXT,
            status TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        conn.commit()
        conn.close()

    def init_songs_table(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT    NOT NULL UNIQUE,
                title       TEXT    NOT NULL,
                artist      TEXT    NOT NULL
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_songs_title ON songs (title)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs (artist)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_songs_filename ON songs (filename)')

        # Insertar datos si la tabla está vacía
        c.execute('SELECT COUNT(*) FROM songs')
        if c.fetchone()[0] == 0:
            self._insert_song_data(c)
        conn.commit()
        conn.close()

    def _insert_song_data(self, cursor):
        songs_data = [
            ('001.mp3', 'Wonderwall', 'Oasis'),
            ('002.mp3', 'Dai Dai', 'Shakira'),
            ('003.mp3', 'Goals', 'Lisa'),
            ('004.mp3', 'NuevaYol', 'Bad Bunny'),
            ('005.mp3', 'Vitamina', 'Jombriel'),
            ('006.mp3', 'Nuestro Juramento', 'Julio Jaramillo'),
            ('007.mp3', 'Shape of you', 'Ed Sheeran'),
            ('008.mp3', 'Numb', 'Linkink Park'),
            ('009.mp3', 'Believer', 'Imagine Dragons'),
            ('010.mp3', 'Billie Jean', 'Michael Jackson'),
            ('011.mp3', 'Viva la vida', 'Coldplay'),
            ('012.mp3', 'Bohemian Rhapsody', 'Queen'),
            ('013.mp3', 'Hey Jude', 'The Beatles'),
            ('014.mp3', 'Lose Yourself', 'Eminem'),
            ('015.mp3', 'Waka Waka', 'Shakira'),
            ('016.mp3', 'Despacito', 'Luis Fonsi'),
            ('017.mp3', 'Musica Ligera', 'Soda Stereo'),
            ('018.mp3', 'Oye mi amor', 'Mana'),
            ('019.mp3', 'Devuelve a mi chica', 'Hombres G'),
            ('020.mp3', 'Lamento Boliviano', 'Enanitos Verdes'),
            ('021.mp3', 'Nunca es Suficiente', 'Natalia Lafourcade'),
            ('022.mp3', 'Still D.R.E', 'Snoop Dogg'),
            ('023.mp3', 'La Copa de la Vida', 'Ricky Martin'),
            ('024.mp3', 'Waving Flag', 'David Bisbal'),
            ('025.mp3', 'El Telefono', 'Hector El Father'),
            ('026.mp3', 'Beat It', 'Michael Jackson'),
            ('027.mp3', 'Uptown Funk', 'Bruno Mars'),
            ('028.mp3', 'Hips Don\'t Lie', 'Shakira'),
            ('029.mp3', 'Havana', 'Camila Cabello'),
            ('030.mp3', 'Apt', 'Rose'),
            ('031.mp3', 'Strategy', 'Twice'),
            ('032.mp3', 'Crazy', 'Lserafim'),
            ('033.mp3', 'Rude', 'Hearts2Hearts'),
            ('034.mp3', 'Imitadora', 'Romeo Santos'),
            ('035.mp3', 'Bailando', 'Enrique Iglesias'),
            ('036.mp3', 'El Baño', 'Enrique Iglesias'),
            ('037.mp3', 'Rockstar', 'Duki'),
            ('038.mp3', 'Feel Me', 'Trueno'),
            ('039.mp3', 'Real Gansta Love', 'Trueno'),
            ('040.mp3', 'Gangnam Style', 'Psy'),
            ('041.mp3', 'Gentleman', 'Psy'),
            ('042.mp3', 'La Macarena', 'Los del rio'),
            ('043.mp3', 'Aserejé', 'Las Ketchup'),
            ('044.mp3', 'Espresso', 'Sabrina Carpentier'),
            ('045.mp3', 'Traicionera', 'Sebastian Yatra'),
            ('046.mp3', 'Justicia', 'Natti Natasha'),
            ('047.mp3', 'Colors', 'Jason Derulo'),
            ('048.mp3', 'Yo me enamore', 'Amar Azul'),
            ('049.mp3', 'Dreamers', 'Jungkook'),
            ('050.mp3', 'Dynamite', 'BTS'),
            ('051.mp3', 'Kill this love', 'BlackPink'),
            ('052.mp3', 'Feel Special', 'Twice'),
            ('053.mp3', 'Amapola', 'Papaya Dada'),
            ('054.mp3', 'Ayayay', 'Papaya Dada'),
            ('055.mp3', 'Cumbia Chonera', 'Don Medardo y sus players'),
            ('056.mp3', 'Solo tu', 'Don Medardo y sus players'),
            ('057.mp3', 'Sugar', 'Maroon 5'),
            ('058.mp3', 'Adan y Eva', 'Paulo Londra'),
            ('059.mp3', 'Tal Vez', 'Paulo Londra'),
            ('060.mp3', 'Nena Maldicion', 'Paulo Londra'),
            ('061.mp3', 'Me Rehuso', 'Danny Ocean'),
            ('062.mp3', 'Chantaje', 'Shakira'),
            ('063.mp3', 'Dance Crip', 'Trueno'),
            ('064.mp3', 'Amorfoda', 'Bad Bunny'),
            ('065.mp3', 'Botella tras botella', 'Cristian Nodal'),
            ('066.mp3', 'Rolling in the deep', 'Adele'),
            ('067.mp3', 'Wake me up', 'Avicii'),
            ('068.mp3', 'The nights', 'Avicii'),
            ('069.mp3', 'Alone', 'Marshmello'),
            ('070.mp3', 'Stars', 'Marshmello'),
            ('071.mp3', 'Happier', 'Marshmello'),
            ('072.mp3', 'Radioactive', 'Imagine Dragons'),
            ('073.mp3', 'Whatever It Takes', 'Imagine Dragons'),
            ('074.mp3', 'Take me to the beach', 'Imagine Dragons'),
            ('075.mp3', 'Levitating', 'Dua Lipa'),
            ('076.mp3', 'Blank Space', 'Taylor Swift'),
            ('077.mp3', 'Shake It Off', 'Taylor Swift'),
            ('078.mp3', 'Bad Blood', 'Taylor Swift'),
            ('079.mp3', 'Play Hard', 'David Guetta'),
            ('080.mp3', 'Butter', 'BTS'),
            ('081.mp3', 'Fairytale', 'Alexander Rybak'),
            ('082.mp3', 'Arcade', 'Duncan Laurence'),
            ('083.mp3', 'Runaway', 'Sunstroke'),
            ('084.mp3', 'Love Me Again', 'John Newman'),
            ('085.mp3', 'Duvet', 'Boa'),
            ('086.mp3', 'Blinding Lights', 'The Weekend'),
            ('087.mp3', 'Never Gonna Give you Up', 'Rick Astley'),
            ('088.mp3', 'Take on me', 'a-ha'),
            ('089.mp3', 'Imagine', 'John Lennon'),
            ('090.mp3', 'Deslocado', 'Napa'),
            ('091.mp3', 'Tren al Sur', 'Los Prisioneros'),
            ('092.mp3', 'My Ordinary Life', 'The Living Tombstone'),
            ('093.mp3', 'Life Goes On', 'Oliver Tree'),
            ('094.mp3', 'Firework', 'Katy Perry'),
            ('095.mp3', 'Let It Be', 'The Beatles'),
            ('096.mp3', 'In the end', 'Linkink Park'),
            ('097.mp3', 'What I have done', 'Linkink Park'),
            ('098.mp3', 'Faint', 'Linkink Park'),
            ('099.mp3', 'El alma en los labios', 'Julio Jaramillo'),
            ('100.mp3', 'El aguacate', 'Julio Jaramillo'),
            ('101.mp3', 'La corriente', 'Mirella Cesa'),
            ('102.mp3', 'El embrujo', 'Americo'),
            ('103.mp3', 'Cariñito', 'Los Kipus'),
            ('104.mp3', 'Perdoname', 'Deorro'),
            ('105.mp3', 'Parte y Choque', 'Jombriel')
        ]
        cursor.executemany(
            'INSERT INTO songs (filename, title, artist) VALUES (?, ?, ?)',
            songs_data
        )

    # ========== MÉTODOS DE BÚSQUEDA DE CANCIONES ==========
    def _normalize_query(self, query):
        """Limpia la consulta eliminando palabras comunes que son errores de transcripción."""
        if not query:
            return ""
        query_lower = query.lower().strip()
        # Palabras que se deben eliminar completamente (verbos, muletillas, errores)
        palabras_eliminar = [
            'pon', 'reproduce', 'toca', 'escuchar', 'quiero', 'poner', 
            'reproducir', 'musica', 'cancion', 'ponme', 'coloca', 'pasa',
            'de', 'la', 'el', 'los', 'las', 'un', 'una', 'algo', 'una', 
            'por', 'favor', 'favor',
            'bon', 'don', 'on', 'buen', 'bom', 'dom', 'om', 'bem',
            'als', 'allas'
        ]
        # Usar regex para eliminar solo palabras completas
        for palabra in palabras_eliminar:
            patron = r'\b' + re.escape(palabra) + r'\b'
            query_lower = re.sub(patron, '', query_lower)
        # Eliminar signos de puntuación y espacios extra
        query_lower = re.sub(r'[^\w\s]', '', query_lower)
        query_lower = ' '.join(query_lower.split())
        return query_lower

    def search_songs(self, query):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Normalizar la consulta
        query_lower = self._normalize_query(query)
        
        # Si después de limpiar queda vacío, buscar por el query original
        if not query_lower:
            query_lower = query.lower().strip()
        
        # Buscar por coincidencia parcial en título o artista
        q = f'%{query_lower}%'
        c.execute('''
            SELECT filename, title, artist FROM songs
            WHERE LOWER(title) LIKE ? OR LOWER(artist) LIKE ?
            ORDER BY title
        ''', (q, q))
        rows = c.fetchall()
        conn.close()
        return [{'filename': r[0], 'title': r[1], 'artist': r[2]} for r in rows]

    def get_random_song(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT filename, title, artist FROM songs ORDER BY RANDOM() LIMIT 1')
        row = c.fetchone()
        conn.close()
        if row:
            return {'filename': row[0], 'title': row[1], 'artist': row[2]}
        return None

    # === Métodos existentes ===
    def add_history(self, user_input, bot_response, intent):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO history (user_input, bot_response, intent) VALUES (?, ?, ?)",
                  (user_input, bot_response, intent))
        conn.commit()
        conn.close()

    def get_history(self, limit=20):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT timestamp, user_input, bot_response, intent FROM history ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return rows

    def add_device(self, name, ip, port, type="esp32", status="active"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO devices (name, ip, port, type, status) VALUES (?, ?, ?, ?, ?)",
                  (name, ip, port, type, status))
        conn.commit()
        conn.close()

    def get_devices(self):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name, ip, port, type, status FROM devices")
        rows = c.fetchall()
        conn.close()
        return rows

    def get_setting(self, key, default=None):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else default

    def set_setting(self, key, value):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()