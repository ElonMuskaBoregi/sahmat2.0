import streamlit as st
import chess
import chess.engine
import chess.svg
from io import StringIO
import base64
import time
import random
import re

# Sayfa konfigürasyonu
st.set_page_config(
    page_title="Şah Mat v1.2",
    page_icon="AI chess",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS stilleri
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Crimson+Text:wght@400;600&display=swap');
    
    .main-header {
        font-family: 'Playfair Display', serif;
        font-size: 3.5rem;
        font-weight: 700;
        text-align: center;
        color: #2c3e50;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .subtitle {
        font-family: 'Crimson Text', serif;
        font-size: 1.3rem;
        text-align: center;
        color: #7f8c8d;
        margin-bottom: 2rem;
        font-style: italic;
    }
    
    .game-status {
        font-family: 'Crimson Text', serif;
        font-size: 1.2rem;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .status-thinking {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .status-your-turn {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
    }
    
    .status-game-over {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        color: #2c3e50;
    }
    
    .move-history {
        font-family: 'Crimson Text', serif;
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #3498db;
        max-height: 300px;
        overflow-y: auto;
    }
    
    .difficulty-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-family: 'Crimson Text', serif;
        font-weight: 600;
        margin: 0.2rem;
    }
    
    .diff-beginner { background: #e8f5e8; color: #2e7d32; }
    .diff-intermediate { background: #fff3e0; color: #f57c00; }
    .diff-advanced { background: #ffebee; color: #c62828; }
    .diff-master { background: #f3e5f5; color: #7b1fa2; }
    .diff-grandmaster { background: #e8eaf6; color: #303f9f; }
    
    .sidebar .stSelectbox > div > div {
        font-family: 'Crimson Text', serif;
    }
    
    .chess-board {
        border: 3px solid #34495e;
        border-radius: 10px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .stats-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class ChessAI:
    def __init__(self, difficulty_level=3):
        self.difficulty_level = difficulty_level
        self.position_values = {
            chess.PAWN: 100,
            chess.KNIGHT: 320,
            chess.BISHOP: 330,
            chess.ROOK: 500,
            chess.QUEEN: 900,
            chess.KING: 20000
        }
        
        # Pozisyon tabloları (merkez kontrolü için)
        self.pawn_table = [
            0,  0,  0,  0,  0,  0,  0,  0,
            50, 50, 50, 50, 50, 50, 50, 50,
            10, 10, 20, 30, 30, 20, 10, 10,
            5,  5, 10, 25, 25, 10,  5,  5,
            0,  0,  0, 20, 20,  0,  0,  0,
            5, -5,-10,  0,  0,-10, -5,  5,
            5, 10, 10,-20,-20, 10, 10,  5,
            0,  0,  0,  0,  0,  0,  0,  0
        ]
        
        self.knight_table = [
            -50,-40,-30,-30,-30,-30,-40,-50,
            -40,-20,  0,  0,  0,  0,-20,-40,
            -30,  0, 10, 15, 15, 10,  0,-30,
            -30,  5, 15, 20, 20, 15,  5,-30,
            -30,  0, 15, 20, 20, 15,  0,-30,
            -30,  5, 10, 15, 15, 10,  5,-30,
            -40,-20,  0,  5,  5,  0,-20,-40,
            -50,-40,-30,-30,-30,-30,-40,-50
        ]
        
        # Hamleleri öncelik sırasına göre sıralamak için
        self.move_ordering_cache = {}

    def order_moves(self, board, moves):
        """Hamleleri değer sırasına göre sırala - daha iyi hamleleri önce değerlendir"""
        scored_moves = []
        
        for move in moves:
            score = 0
            
            # Alma hamleleri - yüksek değerli taşları alma
            if board.is_capture(move):
                victim = board.piece_at(move.to_square)
                attacker = board.piece_at(move.from_square)
                if victim and attacker:
                    # MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
                    score += (self.position_values[victim.piece_type] - 
                             self.position_values[attacker.piece_type] // 10)
            
            # Şah çekme hamleleri
            board.push(move)
            if board.is_check():
                score += 50
            board.pop()
            
            # Merkez kontrol hamleleri
            if move.to_square in [chess.D4, chess.D5, chess.E4, chess.E5]:
                score += 20
            
            # Piyon terfisi
            if board.piece_at(move.from_square) and board.piece_at(move.from_square).piece_type == chess.PAWN:
                if chess.square_rank(move.to_square) in [0, 7]:  # Son sıra
                    score += 800
            
            scored_moves.append((score, move))
        
        # Yüksek skordan düşük skora sırala
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        return [move for score, move in scored_moves]

    def evaluate_position(self, board):
        if board.is_checkmate():
            return -20000 if board.turn else 20000
        if board.is_stalemate() or board.is_insufficient_material():
            return 0
            
        score = 0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = self.position_values[piece.piece_type]
                
                # Pozisyon bonusları
                if piece.piece_type == chess.PAWN:
                    if piece.color == chess.WHITE:
                        value += self.pawn_table[square]
                    else:
                        value += self.pawn_table[63 - square]
                elif piece.piece_type == chess.KNIGHT:
                    if piece.color == chess.WHITE:
                        value += self.knight_table[square]
                    else:
                        value += self.knight_table[63 - square]
                
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value
        
        # Merkez kontrolü
        center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
        for square in center_squares:
            if board.is_attacked_by(chess.WHITE, square):
                score += 10
            if board.is_attacked_by(chess.BLACK, square):
                score -= 10
        
        # Kale sütunu kontrolü
        for file in range(8):
            file_squares = [chess.square(file, rank) for rank in range(8)]
            white_pawns = sum(1 for sq in file_squares if board.piece_at(sq) and 
                            board.piece_at(sq).piece_type == chess.PAWN and 
                            board.piece_at(sq).color == chess.WHITE)
            black_pawns = sum(1 for sq in file_squares if board.piece_at(sq) and 
                            board.piece_at(sq).piece_type == chess.PAWN and 
                            board.piece_at(sq).color == chess.BLACK)
            
            if white_pawns == 0 and black_pawns == 0:  # Açık sütun
                for sq in file_squares:
                    piece = board.piece_at(sq)
                    if piece and piece.piece_type == chess.ROOK:
                        if piece.color == chess.WHITE:
                            score += 20
                        else:
                            score -= 20
        
        return score

    def minimax(self, board, depth, alpha, beta, maximizing_player):
        if depth == 0 or board.is_game_over():
            return self.evaluate_position(board)
        
        # Hamleleri sırala - daha iyi hamleleri önce değerlendir (alpha-beta için önemli)
        legal_moves = list(board.legal_moves)
        ordered_moves = self.order_moves(board, legal_moves)
        
        if maximizing_player:
            max_eval = float('-inf')
            for move in ordered_moves:
                board.push(move)
                eval_score = self.minimax(board, depth - 1, alpha, beta, False)
                board.pop()
                max_eval = max(max_eval, eval_score)
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Alpha-beta pruning
            return max_eval
        else:
            min_eval = float('inf')
            for move in ordered_moves:
                board.push(move)
                eval_score = self.minimax(board, depth - 1, alpha, beta, True)
                board.pop()
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha-beta pruning
            return min_eval

    def get_best_move(self, board):
        legal_moves = list(board.legal_moves)
        if not legal_moves:
            return None
        
        # Az hamle varsa hızlı karar ver
        if len(legal_moves) <= 3:
            return legal_moves[0]
        
        best_move = None
        best_score = float('inf')
        
        # Zorluk seviyesine göre derinlik ayarla - daha agresif optimizasyon
        if self.difficulty_level <= 2:
            depth = 2  # Çok hızlı
        elif self.difficulty_level == 3:
            depth = 3  # Orta
        else:
            depth = 4  # Zor
        
        # Hamleleri sırala
        ordered_moves = self.order_moves(board, legal_moves)
        
        # İlk X hamleyi değerlendir (zorluk seviyesine göre)
        max_moves_to_evaluate = min(len(ordered_moves), 8 + self.difficulty_level * 2)
        moves_to_evaluate = ordered_moves[:max_moves_to_evaluate]
        
        for move in moves_to_evaluate:
            board.push(move)
            score = self.minimax(board, depth, float('-inf'), float('inf'), True)
            board.pop()
            
            if score < best_score:
                best_score = score
                best_move = move
        
        return best_move

def parse_move_input(move_input, board):
    """Kullanıcının girdiği hamleyi parse et - hem uzun hem kısa notasyonu destekle"""
    move_input = move_input.strip().lower()
    
    # Özel durumlar (roklar)
    if move_input in ["o-o", "0-0"]:
        return "O-O"
    if move_input in ["o-o-o", "0-0-0"]:
        return "O-O-O"
    
    # Türkçe taş harflerini İngilizce'ye çevir
    piece_mapping = {
        'a': 'N',  # At -> Knight
        'f': 'B',  # Fil -> Bishop  
        'k': 'R',  # Kale -> Rook
        'v': 'Q',  # Vezir -> Queen
        's': 'K'   # Şah -> King
    }
    
    # Piyon terfisi mapping
    promotion_mapping = {
        'v': 'Q',  # Vezir
        'k': 'R',  # Kale
        'f': 'B',  # Fil
        'a': 'N'   # At
    }
    
    # Piyon terfisi kontrolü
    if '=' in move_input:
        parts = move_input.split('=')
        if len(parts) == 2 and parts[1] in promotion_mapping:
            move_input = parts[0] + '=' + promotion_mapping[parts[1]]
    
    # Uzun notasyon kontrolü (e2e4 gibi)
    if len(move_input) >= 4 and move_input[0].isalpha() and move_input[1].isdigit() and move_input[2].isalpha() and move_input[3].isdigit():
        # Bu zaten uzun notasyon, direkt kullan
        try:
            # Hamleyi parse etmeye çalış
            move = chess.Move.from_uci(move_input)
            if move in board.legal_moves:
                return move_input.upper()
        except:
            pass
    
    # Kısa notasyon (ae4, fe5 gibi) - taş harf + hedef kare
    if len(move_input) >= 3 and move_input[0] in piece_mapping:
        english_piece = piece_mapping[move_input[0]]
        target_square = move_input[1:]
        converted_move = english_piece + target_square
        
        try:
            # Hamleyi parse etmeye çalış
            move = board.parse_san(converted_move)
            if move in board.legal_moves:
                return converted_move
        except:
            pass
    
    # Piyon hamlesi kontrolü (e4, d5 gibi - sadece kare belirtilmiş)
    if len(move_input) == 2 and move_input[0].isalpha() and move_input[1].isdigit():
        try:
            # Direkt kısa notasyon olarak parse etmeye çalış
            move = board.parse_san(move_input)
            if move in board.legal_moves:
                return move_input
        except:
            pass
    
    # Hiçbiri çalışmazsa, orijinal input'u döndür
    return move_input

def turkish_to_english_notation(turkish_move):
    """Türkçe hamle notasyonunu İngilizce'ye çevir - sadece gösterim için"""
    # Özel durumlar
    if turkish_move.upper() == "O-O" or turkish_move.upper() == "0-0":
        return "O-O"
    if turkish_move.upper() == "O-O-O" or turkish_move.upper() == "0-0-0":
        return "O-O-O"
    
    # Türkçe taş harflerini İngilizce'ye çevir
    piece_mapping = {
        'a': 'N',  # At -> Knight
        'f': 'B',  # Fil -> Bishop  
        'k': 'R',  # Kale -> Rook
        'v': 'Q',  # Vezir -> Queen
        's': 'K'   # Şah -> King
    }
    
    # Piyon terfisi kontrolü (örn: e8=v -> e8=Q)
    promotion_mapping = {
        'v': 'Q',  # Vezir
        'k': 'R',  # Kale
        'f': 'B',  # Fil
        'a': 'N'   # At
    }
    
    move = turkish_move.strip()
    
    # Piyon terfisi varsa çevir
    if '=' in move:
        parts = move.split('=')
        if len(parts) == 2 and parts[1].lower() in promotion_mapping:
            move = parts[0] + '=' + promotion_mapping[parts[1].lower()]
    
    # Taş harfini çevir
    if len(move) >= 1 and move[0].lower() in piece_mapping:
        move = piece_mapping[move[0].lower()] + move[1:]
    
    return move

def english_to_turkish_notation(english_move):
    """İngilizce hamle notasyonunu Türkçe'ye çevir (gösterim için)"""
    # Özel durumlar
    if english_move == "O-O":
        return "O-O"
    if english_move == "O-O-O":
        return "O-O-O"
    
    # İngilizce taş harflerini Türkçe'ye çevir
    piece_mapping = {
        'N': 'A',  # Knight -> At
        'B': 'F',  # Bishop -> Fil
        'R': 'K',  # Rook -> Kale
        'Q': 'V',  # Queen -> Vezir
        'K': 'S'   # King -> Şah
    }
    
    # Piyon terfisi kontrolü
    promotion_mapping = {
        'Q': 'V',  # Queen -> Vezir
        'R': 'K',  # Rook -> Kale
        'B': 'F',  # Bishop -> Fil
        'N': 'A'   # Knight -> At
    }
    
    move = english_move
    
    # Piyon terfisi varsa çevir
    if '=' in move:
        parts = move.split('=')
        if len(parts) == 2 and parts[1] in promotion_mapping:
            move = parts[0] + '=' + promotion_mapping[parts[1]]
    
    # Taş harfini çevir
    if len(move) >= 1 and move[0] in piece_mapping:
        move = piece_mapping[move[0]] + move[1:]
    
    return move

def init_game():
    if 'board' not in st.session_state:
        st.session_state.board = chess.Board()
        st.session_state.game_history = []
        st.session_state.ai_thinking = False
        st.session_state.game_over = False
        st.session_state.winner = None
        st.session_state.move_count = 0

def render_board(board):
    svg = chess.svg.board(
        board=board,
        size=400,
        style="""
        .square.light { fill: #f0d9b5; }
        .square.dark { fill: #b58863; }
        .square.light.lastmove { fill: #ffe135; }
        .square.dark.lastmove { fill: #dab520; }
        """
    )
    
    b64 = base64.b64encode(svg.encode('utf-8')).decode("utf-8")
    html = f'<div class="chess-board"><img src="data:image/svg+xml;base64,{b64}"/></div>'
    st.markdown(html, unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">♛ Şah Mat v1.2 Beta ♛</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">"Satranç, zihnin jimnastiğidir" - Blaise Pascal</p>', unsafe_allow_html=True)
    
    init_game()
    
    # Sidebar - Oyun Kontrolleri
    with st.sidebar:
        st.markdown("## ⚙️ Oyun Ayarları")
        
        difficulty_options = {
            "Başlangıç (1)": 1,
            "Kolay (2)": 2, 
            "Orta (3)": 3,
            "Zor (4)": 4,
            "Usta (5)": 5
        }
        
        selected_difficulty = st.selectbox(
            "Zorluk Seviyesi",
            options=list(difficulty_options.keys()),
            index=2
        )
        
        difficulty_level = difficulty_options[selected_difficulty]
        
        # Zorluk rozeti
        diff_classes = {
            1: "diff-beginner",
            2: "diff-beginner", 
            3: "diff-intermediate",
            4: "diff-advanced",
            5: "diff-master"
        }
        
        st.markdown(f'<span class="difficulty-badge {diff_classes[difficulty_level]}">{selected_difficulty}</span>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🆕 Yeni Oyun", use_container_width=True):
            st.session_state.board = chess.Board()
            st.session_state.game_history = []
            st.session_state.ai_thinking = False
            st.session_state.game_over = False
            st.session_state.winner = None
            st.session_state.move_count = 0
            st.rerun()
            
        if st.button("🔄 Geri Al", use_container_width=True, disabled=len(st.session_state.game_history) < 2):
            if len(st.session_state.game_history) >= 2:
                # Son iki hamleyi geri al (oyuncu + AI)
                st.session_state.board.pop()
                st.session_state.board.pop()
                st.session_state.game_history = st.session_state.game_history[:-2]
                st.session_state.move_count -= 2
                st.session_state.ai_thinking = False
                st.rerun()
        
        st.markdown("---")
        st.markdown("### 📊 Oyun İstatistikleri")
        st.markdown(f"**Hamle Sayısı:** {st.session_state.move_count}")
        st.markdown(f"**Sıra:** {'Beyaz' if st.session_state.board.turn else 'Siyah'}")
        
        if st.session_state.board.is_check():
            st.markdown("⚠️ **ŞAH!**")
            
        # Hamle geçmişi
        st.markdown("### 📝 Hamle Geçmişi")
        if st.session_state.game_history:
            history_text = ""
            for i, move in enumerate(st.session_state.game_history):
                if i % 2 == 0:
                    history_text += f"{i//2 + 1}. {move} "
                else:
                    history_text += f"{move}\n"
            st.markdown(f'<div class="move-history">{history_text}</div>', unsafe_allow_html=True)
    
    # Ana oyun alanı
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Oyun durumu
        if st.session_state.ai_thinking:
            st.markdown('<div class="game-status status-thinking">🤔 AI düşünüyor...</div>', unsafe_allow_html=True)
        elif st.session_state.game_over:
            if st.session_state.winner:
                st.markdown(f'<div class="game-status status-game-over">🏆 {st.session_state.winner} kazandı!</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="game-status status-game-over">🤝 Berabere!</div>', unsafe_allow_html=True)
        else:
            if st.session_state.board.turn:
                st.markdown('<div class="game-status status-your-turn">♔ Sizin sıranız (Beyaz)</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="game-status status-thinking">♛ AI\'nın sırası (Siyah)</div>', unsafe_allow_html=True)
        
        # Satranç tahtası
        render_board(st.session_state.board)
    
    with col2:
        st.markdown("### 🎯 Hamle Yap")
        
        if not st.session_state.game_over and st.session_state.board.turn and not st.session_state.ai_thinking:
            # Kullanıcı hamlesi için input
            user_move = st.text_input(
                "Hamlenizi girin:",
                key="move_input",
                placeholder="e4, d5, ae4, fc5, e2e4"
            )
            
            if st.button("Hamle Yap", use_container_width=True) and user_move:
                try:
                    # Hamleyi parse et (yeni fonksiyon)
                    parsed_input = parse_move_input(user_move, st.session_state.board)
                    
                    # Hamleyi chess kütüphanesi ile parse etmeye çalış
                    if parsed_input.upper() in ["O-O", "O-O-O"]:
                        # Roklar için özel işlem
                        move = st.session_state.board.parse_san(parsed_input)
                    elif len(parsed_input) == 4 and parsed_input[0].isalpha() and parsed_input[1].isdigit():
                        # UCI formatı (e2e4 gibi)
                        move = chess.Move.from_uci(parsed_input.lower())
                    else:
                        # SAN formatı (e4, Nf3 gibi)
                        move = st.session_state.board.parse_san(parsed_input)
                    
                    if move in st.session_state.board.legal_moves:
                        # Hamleyi yapmadan önce notasyonu al
                        move_notation = st.session_state.board.san(move)
                        
                        # Kullanıcı hamlesi
                        st.session_state.board.push(move)
                        
                        # Hamle geçmişine kullanıcının girdiği hareketi kaydet
                        st.session_state.game_history.append(user_move)
                        st.session_state.move_count += 1
                        
                        # Oyun bitimi kontrolü
                        if st.session_state.board.is_game_over():
                            st.session_state.game_over = True
                            if st.session_state.board.is_checkmate():
                                st.session_state.winner = "Beyaz"
                            else:
                                st.session_state.winner = None
                        else:
                            st.session_state.ai_thinking = True
                        
                        st.rerun()
                    else:
                        st.error("Geçersiz hamle! Lütfen geçerli bir hamle girin.")
                        
                except Exception as e:
                    st.error(f"Hamle formatı hatalı! Lütfen doğru formatı kullanın. Hata: {str(e)}")
        
        # AI hamle mantığı - OPTIMIZED: time.sleep kaldırıldı
        if not st.session_state.game_over and not st.session_state.board.turn and st.session_state.ai_thinking:
            ai = ChessAI(difficulty_level)
            ai_move = ai.get_best_move(st.session_state.board)
            
            if ai_move:
                # Hamleyi yapmadan önce notasyonu al
                move_san = st.session_state.board.san(ai_move)
                
                # AI hamlesi
                st.session_state.board.push(ai_move)
                
                # AI hamlesini Türkçe notasyonla kaydet
                turkish_notation = english_to_turkish_notation(move_san)
                st.session_state.game_history.append(turkish_notation)
                st.session_state.move_count += 1
                
                # Oyun bitimi kontrolü
                if st.session_state.board.is_game_over():
                    st.session_state.game_over = True
                    if st.session_state.board.is_checkmate():
                        st.session_state.winner = "Siyah (AI)"
                    else:
                        st.session_state.winner = None
            
            st.session_state.ai_thinking = False
            st.rerun()
        
        # Hamle önerileri
        if not st.session_state.game_over and st.session_state.board.turn and not st.session_state.ai_thinking:
            st.markdown("### 💡 Hamle Önerileri")
            
            # Hızlı öneri sistemi - sadece birkaç hamleyi değerlendir
            legal_moves = list(st.session_state.board.legal_moves)
            if legal_moves:
                # En fazla 3 öneri göster, rastgele seç
                sample_size = min(3, len(legal_moves))
                suggested_moves = random.sample(legal_moves, sample_size)
                
                for move in suggested_moves:
                    move_san = st.session_state.board.san(move)
                    turkish_move = english_to_turkish_notation(move_san)
                    
                    # Hamle tipini belirle
                    move_type = ""
                    if st.session_state.board.is_capture(move):
                        move_type = "🎯 Alma"
                    elif st.session_state.board.gives_check(move):
                        move_type = "⚔️ Şah"
                    elif move.to_square in [chess.D4, chess.D5, chess.E4, chess.E5]:
                        move_type = "🎪 Merkez"
                    else:
                        move_type = "📍 Normal"
                    
                    st.markdown(f"• **{turkish_move}** {move_type}")
        
        # Oyun ipuçları
        st.markdown("### 📚 Hamle Formatları")
        st.markdown("""
        **Piyon:** e4, d5, a6  
        **At:** ae4, ag5  
        **Fil:** fc4, fd3  
        **Kale:** kd1, ka8  
        **Vezir:** vd4, ve5  
        **Şah:** sg1, sk1  
        **Rok:** O-O (kısa), O-O-O (uzun)  
        **Uzun:** e2e4, g1f3
        """)
        
        if not st.session_state.game_over:
            st.markdown("### ⚡ Kazanma Olasılığı")
            
            # Hızlı pozisyon değerlendirmesi
            def calculate_win_probability():
                # Malzeme sayımı
                white_material = 0
                black_material = 0
                
                piece_values = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330, 
                              chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
                
                for square in chess.SQUARES:
                    piece = st.session_state.board.piece_at(square)
                    if piece:
                        value = piece_values.get(piece.piece_type, 0)
                        if piece.color == chess.WHITE:
                            white_material += value
                        else:
                            black_material += value
                
                # Pozisyon faktörleri
                position_score = 0
                
                # Merkez kontrolü
                center_squares = [chess.D4, chess.D5, chess.E4, chess.E5]
                for square in center_squares:
                    if st.session_state.board.is_attacked_by(chess.WHITE, square):
                        position_score += 20
                    if st.session_state.board.is_attacked_by(chess.BLACK, square):
                        position_score -= 20
                
                # Hamle özgürlüğü
                current_turn = st.session_state.board.turn
                legal_moves = len(list(st.session_state.board.legal_moves))
                
                # Sıra değiştir ve rakip hamle sayısını al
                st.session_state.board.turn = not current_turn
                opponent_moves = len(list(st.session_state.board.legal_moves))
                st.session_state.board.turn = current_turn
                
                mobility_score = (legal_moves - opponent_moves) * 5
                if not current_turn:  # Siyahın sırası ise tersine çevir
                    mobility_score = -mobility_score
                
                # Şah durumu
                check_bonus = 0
                if st.session_state.board.is_check():
                    check_bonus = 50 if current_turn == chess.BLACK else -50
                
                # Toplam skor
                total_score = (white_material - black_material) + position_score + mobility_score + check_bonus
                
                # Skoru yüzdeye çevir (-1000 ile +1000 arası normalize et)
                normalized_score = max(-1000, min(1000, total_score))
                win_percentage = 50 + (normalized_score / 1000) * 40  # 10-90 arası
                
                return win_percentage, white_material - black_material
            
            win_prob, material_diff = calculate_win_probability()
            
            # Kazanma olasılığı barı
            white_prob = win_prob
            black_prob = 100 - win_prob
            
            # Renk belirleme
            if white_prob > 65:
                bar_color = "linear-gradient(90deg, #2ecc71 0%, #27ae60 100%)"
                status_text = "🔥 Beyaz Baskın"
            elif white_prob > 55:
                bar_color = "linear-gradient(90deg, #f39c12 0%, #e67e22 100%)"
                status_text = "📈 Beyaz Avantajlı"
            elif white_prob > 45:
                bar_color = "linear-gradient(90deg, #95a5a6 0%, #7f8c8d 100%)"
                status_text = "⚖️ Dengeli"
            elif white_prob > 35:
                bar_color = "linear-gradient(90deg, #e74c3c 0%, #c0392b 100%)"
                status_text = "📉 Siyah Avantajlı"
            else:
                bar_color = "linear-gradient(90deg, #8e44ad 0%, #9b59b6 100%)"
                status_text = "🔥 Siyah Baskın"
            
            # Progress bar HTML
            st.markdown(f"""
            <div style="background: #ecf0f1; border-radius: 20px; overflow: hidden; margin: 10px 0;">
                <div style="
                    background: {bar_color};
                    width: {white_prob}%;
                    height: 30px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-weight: bold;
                    font-family: 'Crimson Text', serif;
                    transition: width 0.5s ease;
                ">
                    {white_prob:.1f}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**Durum:** {status_text}")
            
            # Detay bilgiler
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**♔ Beyaz:** {white_prob:.1f}%")
            with col_b:
                st.markdown(f"**♛ Siyah:** {black_prob:.1f}%")
            
            # Malzeme durumu
            if material_diff > 0:
                st.markdown(f"**Malzeme:** Beyaz +{material_diff//100}")
            elif material_diff < 0:
                st.markdown(f"**Malzeme:** Siyah +{abs(material_diff)//100}")
            else:
                st.markdown("**Malzeme:** Eşit")
            
            # Hamle sayıları
            legal_move_count = len(list(st.session_state.board.legal_moves))
            st.markdown(f"**Hamle Seçenekleri:** {legal_move_count}")
            
            if st.session_state.board.is_check():
                st.markdown("🚨 **ŞAH!**")

    # Alt kısım - Oyun Bilgileri
    st.markdown("---")
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        st.markdown("### 🏆 Kazanma Koşulları")
        st.markdown("""
        • **Şah Mat:** Rakip şahını kaçışsız tehdit et
        • **Zaman:** Rakip zaman aşımına uğrasın
        • **Teslim:** Rakip oyunu teslim etsin
        """)
    
    with col4:
        st.markdown("### ⚖️ Beraberlik Koşulları")
        st.markdown("""
        • **Pat:** Şah değil ama hamle yok
        • **50 Hamle:** 50 hamle piyon/alma yok
        • **Tekrar:** Aynı pozisyon 3 kez
        • **Malzeme Yetersiz:** Mat edilemez
        """)
    
    with col5:
        st.markdown("### 🎯 Strateji İpuçları")
        st.markdown("""
        • **Açılış:** Merkez kontrolü
        • **Orta Oyun:** Taktiksel fırsatlar
        • **Son Oyun:** Piyon terfi
        • **Güvenlik:** Şahını koru
        """)


if __name__ == "__main__":
    main()
        