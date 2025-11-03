import streamlit as st
import pandas as pd
import numpy as np
from sha256 import sha256_trace
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Configuration de la page
st.set_page_config(
    page_title="SHA-256 — Démo pas-à-pas",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation des variables de session
if 'trace' not in st.session_state:
    st.session_state.trace = None
if 'current_block' not in st.session_state:
    st.session_state.current_block = 0
if 'current_round' not in st.session_state:
    st.session_state.current_round = 0
if 'hash1' not in st.session_state:
    st.session_state.hash1 = None
if 'hash2' not in st.session_state:
    st.session_state.hash2 = None
if 'auto_play' not in st.session_state:
    st.session_state.auto_play = False
if 'play_speed' not in st.session_state:
    st.session_state.play_speed = 0.5  # Vitesse en secondes entre chaque round
if 'refresh_count' not in st.session_state:
    st.session_state.refresh_count = 0

# Titre principal
st.title("🔐 SHA-256 — Démo pas-à-pas")

# Sidebar pour les contrôles
with st.sidebar:
    st.header("⚙️ Contrôles")

    # Upload de fichier
    uploaded_file = st.file_uploader("Ouvrir un fichier", type=None)
    if uploaded_file is not None:
        content = uploaded_file.read()
        st.session_state.uploaded_content = content.decode('utf-8', errors='replace')

    st.markdown("---")

    # Explications
    with st.expander("📖 Explications", expanded=False):
        st.markdown("""
        **Padding** : Le padding ajoute des bits pour atteindre une taille multiple de 512 bits
        
        **Schedule** : Création du schedule W[0..63] avec expansion des mots
        
        **Rounds** : 64 rounds de compression avec mise à jour des registres a..h
        
        **Comparaison** : Visualisation bit à bit des différences entre deux hash
        """)


# Onglets principaux
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📝 Message", "📊 Padding", "📋 Schedule", "🔄 Rounds", "🔍 Comparaison"])

# ===== ONGLET 1: MESSAGE ET HASH =====
with tab1:
    st.header("Message à hacher")

    # Zone de texte pour le message
    if 'uploaded_content' in st.session_state:
        message_input = st.text_area("Entrez votre message:", value=st.session_state.uploaded_content, height=150, key="msg_input")
    else:
        message_input = st.text_area("Entrez votre message:", height=150, key="msg_input")

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔐 Hacher", type="primary"):
            if message_input.strip():
                try:
                    result = sha256_trace(message_input.encode())
                    st.session_state.trace = result
                    st.session_state.current_block = 0
                    st.session_state.current_round = 0
                    st.success("Hash calculé avec succès!")
                except Exception as e:
                    st.error(f"Erreur lors du calcul: {str(e)}")
            else:
                st.warning("Le message ne peut pas être vide")

    # Affichage du digest
    if st.session_state.trace:
        st.markdown("### Digest (hex)")
        st.code(st.session_state.trace['digest'], language=None)

# ===== ONGLET 2: PADDING =====
with tab2:
    st.header("Informations de Padding")

    if st.session_state.trace:
        # Affichage du digest
        st.markdown("### Digest (hex)")
        st.code(st.session_state.trace['digest'], language=None)
        st.markdown("---")
        padding_info = st.session_state.trace['padding']

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Bits de données", padding_info['data_bits'])
            st.metric("Bit '1'", "1")
            st.metric("Zéros de bourrage", padding_info['zero_bits'])
        with col2:
            st.metric("Champ longueur (64 bits)", padding_info['len_bits'])
            st.metric("Total après padding (bits)", padding_info['total_bits'])
            st.metric("Nombre de blocs (512b)", len(st.session_state.trace['blocks']))
    else:
        st.info("Hachez d'abord un message pour voir les informations de padding")

# ===== ONGLET 3: SCHEDULE =====
with tab3:
    st.header("Schedule W[0..63]")

    if st.session_state.trace and st.session_state.trace['blocks']:
        # Affichage du digest
        st.markdown("### Digest (hex)")
        st.code(st.session_state.trace['digest'], language=None)
        st.markdown("---")
        # Contrôles de navigation
        col1, col2, col3 = st.columns([2, 2, 6])
        with col1:
            max_block = len(st.session_state.trace['blocks']) - 1
            # Ne pas écraser current_block si en mode Play
            if not st.session_state.auto_play:
                new_block = st.number_input(
                    "Bloc:",
                    min_value=0,
                    max_value=max_block,
                    value=st.session_state.current_block,
                    key="schedule_block"
                )
                if new_block != st.session_state.current_block:
                    st.session_state.current_block = new_block
            else:
                st.number_input(
                    "Bloc:",
                    min_value=0,
                    max_value=max_block,
                    value=st.session_state.current_block,
                    key="schedule_block_display",
                    disabled=True
                )
        with col2:
            # Ne pas écraser current_round si en mode Play
            if not st.session_state.auto_play:
                new_round = st.number_input(
                    "Round:",
                    min_value=0,
                    max_value=64,
                    value=st.session_state.current_round,
                    key="schedule_round"
                )
                if new_round != st.session_state.current_round:
                    st.session_state.current_round = new_round
            else:
                st.number_input(
                    "Round:",
                    min_value=0,
                    max_value=64,
                    value=st.session_state.current_round,
                    key="schedule_round_display",
                    disabled=True
                )

        # Affichage du schedule
        block = st.session_state.trace['blocks'][st.session_state.current_block]
        schedule = block['schedule']

        # Créer un DataFrame pour l'affichage
        df_schedule = pd.DataFrame({
            'i': range(64),
            'W[i]': [f"0x{w:08x}" for w in schedule]
        })

        # Mettre en évidence le round actuel
        def highlight_row(row):
            if row.name == st.session_state.current_round:
                return ['background-color: #4776e6; color: white'] * len(row)
            return [''] * len(row)

        styled_df = df_schedule.style.apply(highlight_row, axis=1)
        st.dataframe(styled_df, height=600, use_container_width=True)
    else:
        st.info("Hachez d'abord un message pour voir le schedule")

# ===== ONGLET 4: ROUNDS =====
with tab4:
    st.header("Rounds de compression (0..63)")

    if st.session_state.trace and st.session_state.trace['blocks']:
        # Affichage du digest final
        st.markdown("### Hash SHA-256 final")
        st.code(st.session_state.trace['digest'], language=None)

        # Calculer et afficher le hash intermédiaire (concaténation des registres du round actuel)
        # On doit le faire après avoir récupéré round_info, donc on le fera plus bas

        st.markdown("---")
        # Contrôles de navigation
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1.5, 1, 1, 2, 3])

        with col1:
            if st.button("◀◀", key="prev_round"):
                st.session_state.current_round = max(0, st.session_state.current_round - 1)
                st.rerun()

        with col2:
            # Afficher le round actuel (en lecture seule pendant le Play)
            if st.session_state.auto_play:
                st.number_input(
                    "Round:",
                    min_value=0,
                    max_value=64,  # Permettre d'aller jusqu'à 64 (état final)
                    value=st.session_state.current_round,
                    key="rounds_round_display",
                    disabled=True
                )
            else:
                new_round = st.number_input(
                    "Round:",
                    min_value=0,
                    max_value=64,  # Permettre d'aller jusqu'à 64 (état final)
                    value=st.session_state.current_round,
                    key="rounds_round_input"
                )
                # Mettre à jour seulement si changé manuellement
                if new_round != st.session_state.current_round:
                    st.session_state.current_round = new_round

        with col3:
            if st.button("▶▶", key="next_round"):
                st.session_state.current_round = min(64, st.session_state.current_round + 1)  # Max 64
                st.rerun()

        with col4:
            # Bouton Play/Pause
            if st.session_state.auto_play:
                if st.button("⏸ Pause", key="pause_btn", type="secondary"):
                    st.session_state.auto_play = False
                    st.session_state.refresh_count = 0
                    st.rerun()
            else:
                if st.button("▶ Play", key="play_btn", type="primary"):
                    st.session_state.auto_play = True
                    st.session_state.refresh_count = 0  # Réinitialiser le compteur au démarrage
                    st.rerun()

        with col5:
            # Slider de vitesse
            st.session_state.play_speed = st.slider(
                "Vitesse (sec)",
                min_value=0.1,
                max_value=2.0,
                value=st.session_state.play_speed,
                step=0.1,
                key="speed_slider",
                help="Temps en secondes entre chaque round"
            )

        # Logique de lecture automatique
        if st.session_state.auto_play:
            # Convertir la vitesse en millisecondes
            refresh_ms = int(st.session_state.play_speed * 1000)

            # Auto-refresh avec le délai spécifié - retourne le nombre de refreshes
            count = st_autorefresh(interval=refresh_ms, limit=10000, key="auto_refresh")

            # Incrémenter à chaque refresh (count augmente à chaque fois)
            if count > st.session_state.refresh_count:
                st.session_state.refresh_count = count

                # Avancer au round suivant
                if st.session_state.current_round < 64:  # Aller jusqu'à 64 maintenant
                    st.session_state.current_round += 1
                else:
                    # Passer au bloc suivant si disponible
                    if st.session_state.current_block < len(st.session_state.trace['blocks']) - 1:
                        st.session_state.current_block += 1
                        st.session_state.current_round = 0
                    else:
                        # Fin de la lecture
                        st.session_state.auto_play = False
                        st.session_state.refresh_count = 0


        # Récupérer les informations du round
        block = st.session_state.trace['blocks'][st.session_state.current_block]
        round_info = block['rounds'][st.session_state.current_round]

        # Afficher le hash intermédiaire (concaténation des registres a..h)
        intermediate_hash = ''.join(f"{round_info[reg]:08x}" for reg in "abcdefgh")

        # Affichage différent selon le round
        if st.session_state.current_round == 64:
            st.markdown("### ✅ Hash final du bloc (après addition avec H)")
            st.code(intermediate_hash, language=None)
            st.caption("✅ Round 64 : Valeurs finales après addition des registres du round 63 avec H initial (mod 2³²)")
            st.success("🎉 Le hash affiché ci-dessus est le résultat final du bloc !")
        else:
            st.markdown("### État intermédiaire du round actuel")
            st.code(intermediate_hash, language=None)
            if st.session_state.current_round == 63:
                st.caption("⚠️ Round 63 : Dernière itération. Passez au round 64 pour voir le hash final après addition avec H.")
            else:
                st.caption(f"⚠️ Round {st.session_state.current_round} : Concaténation brute des registres a..h (avant addition finale avec H)")

        st.markdown("---")

        # Afficher la progression
        if st.session_state.auto_play:
            st.info(f"▶ Lecture en cours... Bloc {st.session_state.current_block + 1}/{len(st.session_state.trace['blocks'])} - Round {st.session_state.current_round + 1}/64")
            progress = (st.session_state.current_round + 1) / 64
            st.progress(progress)

        # Affichage des registres
        st.markdown("### Registres a..h")
        cols = st.columns(8)
        for i, reg in enumerate("abcdefgh"):
            with cols[i]:
                st.metric(reg.upper(), f"0x{round_info[reg]:08x}")

        st.markdown("---")

        # Affichage des variables T1, T2, K, W (seulement pour les rounds 0-63)
        if st.session_state.current_round < 64:
            st.markdown("### Variables de round")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("T1", f"0x{round_info['T1']:08x}")
            with col2:
                st.metric("T2", f"0x{round_info['T2']:08x}")
            with col3:
                st.metric("K", f"0x{round_info['K']:08x}")
            with col4:
                st.metric("W", f"0x{round_info['W']:08x}")

            st.markdown("---")

            # Affichage des opérations
            st.markdown("### Opérations du round")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Ch(e,f,g)**")
                st.code(f"0x{round_info['Ch']:08x}")
            with col2:
                st.markdown("**Σ1(e)**")
                st.code(f"0x{round_info['Sigma1']:08x}")
            with col3:
                st.markdown("**Maj(a,b,c)**")
                st.code(f"0x{round_info['Maj']:08x}")
        else:
            st.info("Round 64 : État final après addition. Aucune opération n'est effectuée à cette étape.")


# ===== ONGLET 5: COMPARAISON =====
with tab5:
    st.header("Comparaison de deux hash")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Message 1**")
        msg1 = st.text_area("Entrez le premier message:", height=100, key="cmp_msg1")
    with col2:
        st.markdown("**Message 2**")
        msg2 = st.text_area("Entrez le deuxième message:", height=100, key="cmp_msg2")

    if st.button("🔍 Comparer", type="primary"):
        if msg1.strip() and msg2.strip():
            try:
                hash1_result = sha256_trace(msg1.encode())
                hash2_result = sha256_trace(msg2.encode())

                st.session_state.hash1 = hash1_result['digest']
                st.session_state.hash2 = hash2_result['digest']

                st.success("Comparaison effectuée!")
            except Exception as e:
                st.error(f"Erreur lors de la comparaison: {str(e)}")
        else:
            st.warning("Les deux messages doivent être renseignés")

    # Affichage de la comparaison
    if st.session_state.hash1 and st.session_state.hash2:
        st.markdown("### Résultats")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Hash 1**")
            st.code(st.session_state.hash1)
        with col2:
            st.markdown("**Hash 2**")
            st.code(st.session_state.hash2)

        # Conversion en binaire et calcul des différences
        bin1 = bin(int(st.session_state.hash1, 16))[2:].zfill(256)
        bin2 = bin(int(st.session_state.hash2, 16))[2:].zfill(256)
        diff_bits = sum(1 for a, b in zip(bin1, bin2) if a != b)
        diff_percent = (diff_bits / 256) * 100

        st.metric("Différences", f"{diff_bits} bits sur 256 ({diff_percent:.2f}%)")

        # Visualisation matricielle des différences
        st.markdown("### Visualisation des différences (matrice 8x32)")

        # Créer une matrice 8x32
        matrix = np.zeros((8, 32))

        for i in range(256):
            row = i // 32
            col = i % 32
            if bin1[i] != bin2[i]:
                matrix[row][col] = 2  # Rouge pour les différences
            elif bin1[i] == "1":
                matrix[row][col] = 1  # Vert pour les bits à 1 identiques
            else:
                matrix[row][col] = 0  # Gris pour les bits à 0 identiques

        # Créer la heatmap avec 3 couleurs
        # Valeurs: 0 = gris, 1 = vert, 2 = rouge
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            colorscale=[
                [0.0, '#90A4AE'],  # 0 -> gris
                [0.5, '#4CAF50'],  # 1 -> vert
                [1.0, '#ff6b6b']   # 2 -> rouge
            ],
            zmin=0,
            zmax=2,
            showscale=False,
            hovertemplate='Bit %{x},%{y}<extra></extra>'
        ))

        fig.update_layout(
            title="Matrice des bits (256 bits en grille 8×32)",
            xaxis_title="Colonne",
            yaxis_title="Ligne",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Légende minimaliste et jolie
        st.markdown("#### Légende")
        legend_cols = st.columns(3)
        with legend_cols[0]:
            st.markdown("🟩 **Bits à 1** (identiques)")
        with legend_cols[1]:
            st.markdown("⬜ **Bits à 0** (identiques)")
        with legend_cols[2]:
            st.markdown("🟥 **Bits différents**")

