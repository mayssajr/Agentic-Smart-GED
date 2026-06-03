"""
generate_cvs.py
───────────────
Génère 30 CVs PDF réalistes pour tester le système ACE
sur le poste "Ingénieur Systèmes Embarqués" chez AeroTech.

Répartition :
  8 CVs clairement insuffisants  (score attendu 20-44) → Refus évident
  7 CVs limites                  (score attendu 45-64) → Liste attente
  10 CVs bons                    (score attendu 65-82) → Entretien
  5 CVs excellents               (score attendu 83-95) → Entretien prioritaire

Usage :
  python generate_cvs.py
  → Crée un dossier cvs_embarques/ avec 30 fichiers PDF
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT_DIR = "cvs_embarques"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Données des 30 candidats ──────────────────────────────────────────────────
# Format : (nom, email, score_attendu, profil, experience, competences, formation, projets, notes_rh_suggérées)

CANDIDATS = [

    # ═══════════════════════════════════════════════════════════════════════════
    # GROUPE 1 : INSUFFISANTS (score 20-44) — 8 CVs → Refus
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "nom": "Anis Gharbi",
        "email": "anis.gharbi@email.com",
        "tel": "+33 6 11 22 33 44",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 22,
        "groupe": "insuffisant",
        "accroche": "Étudiant en master électronique, passionné par les systèmes numériques et la programmation embarquée.",
        "experience": [
            ("2024 (3 mois)", "Stagiaire - Université Paul Sabatier, Toulouse",
             "Projet académique : simulation d'un PID sur Arduino Uno. Aucun déploiement industriel."),
        ],
        "competences": {
            "Microcontrôleurs": "Arduino Uno, Raspberry Pi (niveau débutant)",
            "Langages": "C basique, Python (scripts simples)",
            "RTOS": "Aucune expérience",
            "Certifications": "Aucune",
            "Protocoles": "UART basique",
        },
        "formation": "Master 1 Électronique Embarquée — Université Paul Sabatier, Toulouse (en cours 2024-2025)",
        "projets": [
            "Robot suiveur de ligne (projet universitaire, Arduino)",
            "LED clignotante avec timer — TP de cours",
        ],
        "langues": "Français (natif), Anglais (B1)",
        "notes_rh": "- Aucune expérience industrielle réelle\n- Arduino et Raspberry Pi seulement, pas de microcontrôleur professionnel\n- FreeRTOS et DO-178C totalement absents\n- Niveau stage uniquement, poste demande minimum 3 ans",
    },

    {
        "nom": "Léa Fontaine",
        "email": "lea.fontaine@email.com",
        "tel": "+33 6 22 33 44 55",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 28,
        "groupe": "insuffisant",
        "accroche": "Ingénieure en informatique générale, souhaitant se reconvertir vers l'embarqué.",
        "experience": [
            ("2022-2025 (3 ans)", "Développeuse web — Agence NovaTech, Paris",
             "Développement React/Node.js. Aucun lien avec l'embarqué ou le temps réel."),
        ],
        "competences": {
            "Microcontrôleurs": "Aucune expérience",
            "Langages": "JavaScript, TypeScript, Python (web)",
            "RTOS": "Aucune connaissance",
            "Certifications": "Aucune",
            "Protocoles": "HTTP/REST uniquement",
        },
        "formation": "Licence Informatique — Université Paris-Est (2022)",
        "projets": [
            "Application web e-commerce (React + Node.js)",
            "API REST pour gestion de stocks",
        ],
        "langues": "Français (natif), Anglais (B2), Espagnol (A2)",
        "notes_rh": "- Profil web/logiciel sans aucun lien avec l'embarqué\n- Reconversion sans formation embarquée démontrée\n- Aucune compétence C embarqué, RTOS, protocoles industriels\n- Hors cible complète",
    },

    {
        "nom": "Omar Ziani",
        "email": "omar.ziani@email.com",
        "tel": "+33 6 33 44 55 66",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 35,
        "groupe": "insuffisant",
        "accroche": "Technicien en électronique avec 2 ans d'expérience en maintenance industrielle.",
        "experience": [
            ("2023-2025 (2 ans)", "Technicien maintenance — Usine Renault, Flins",
             "Maintenance préventive de lignes de production. Pas de développement firmware."),
        ],
        "competences": {
            "Microcontrôleurs": "PLC Siemens (niveau opérateur)",
            "Langages": "Ladder (PLC basique), notions C",
            "RTOS": "Aucune expérience",
            "Certifications": "Habilitation électrique B2V",
            "Protocoles": "Profibus (lecture seule)",
        },
        "formation": "BTS Électronique — Lycée Vaucanson, Tours (2023)",
        "projets": [
            "Remplacement d'automate sur ligne de peinture",
            "Câblage armoire électrique",
        ],
        "langues": "Français (natif), Arabe (natif), Anglais (A2)",
        "notes_rh": "- BTS uniquement, poste nécessite diplôme ingénieur\n- Maintenance hardware ≠ développement firmware embarqué\n- PLC Siemens ≠ STM32, aucun développement bas niveau\n- Pas de C embarqué, FreeRTOS, MISRA-C absents",
    },

    {
        "nom": "Inès Moreau",
        "email": "ines.moreau@email.com",
        "tel": "+33 6 44 55 66 77",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 30,
        "groupe": "insuffisant",
        "accroche": "Ingénieure en traitement du signal, intéressée par les applications embarquées temps réel.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieure signal — Thales Communications, Gennevilliers",
             "Traitement du signal audio/vidéo sur DSP Texas Instruments. Simulation MATLAB."),
        ],
        "competences": {
            "Microcontrôleurs": "DSP TI TMS320 (traitement signal uniquement)",
            "Langages": "MATLAB, C (simulation), Python",
            "RTOS": "Aucune expérience FreeRTOS ou équivalent safety-critical",
            "Certifications": "Aucune (DO-178C non maîtrisée)",
            "Protocoles": "Aucun protocole industriel CAN/SPI",
        },
        "formation": "Master Traitement du Signal — ENSEEIHT, Toulouse (2022)",
        "projets": [
            "Algorithme de débruitage audio en temps réel sur DSP",
            "Simulation MATLAB d'un filtre Kalman",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "- DSP traitement signal ≠ microcontrôleur embarqué critique\n- Aucune expérience aéronautique ou safety-critical\n- MATLAB/simulation ≠ développement firmware production\n- DO-178C, MISRA-C, STM32 absents",
    },

    {
        "nom": "Baptiste Renaud",
        "email": "baptiste.renaud@email.com",
        "tel": "+33 6 55 66 77 88",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 25,
        "groupe": "insuffisant",
        "accroche": "Développeur logiciel embarqué débutant, autodidacte passionné de hardware.",
        "experience": [
            ("2024 (6 mois)", "Alternant développeur IoT — Startup SmartHome, Lyon",
             "Développement firmware ESP32 pour objets connectés grand public. Protocoles WiFi/BLE."),
        ],
        "competences": {
            "Microcontrôleurs": "ESP32, ESP8266 (Arduino framework)",
            "Langages": "C++ (Arduino), MicroPython",
            "RTOS": "FreeRTOS superficiel (Arduino wrapper)",
            "Certifications": "Aucune",
            "Protocoles": "MQTT, BLE, WiFi — aucun CAN/SPI/I2C industriel",
        },
        "formation": "Licence Pro IoT — IUT Bordeaux (2024)",
        "projets": [
            "Station météo connectée ESP32 + MQTT",
            "Domotique maison avec Home Assistant",
        ],
        "langues": "Français (natif), Anglais (B1)",
        "notes_rh": "- ESP32 consumer grade ≠ STM32H7 industriel\n- IoT grand public ≠ embarqué critique aéronautique\n- FreeRTOS via wrapper Arduino, pas de maîtrise réelle\n- Licence Pro insuffisante, expérience < 1 an",
    },

    {
        "nom": "Nadia Benhamou",
        "email": "nadia.benhamou@email.com",
        "tel": "+33 6 66 77 88 99",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 20,
        "groupe": "insuffisant",
        "accroche": "Ingénieure mécanique reconvertie, cherche à évoluer vers les systèmes cyber-physiques.",
        "experience": [
            ("2021-2025 (4 ans)", "Ingénieure mécanique — Airbus Structure, Toulouse",
             "Conception pièces aéronautiques en CATIA V5. Aucun logiciel embarqué."),
        ],
        "competences": {
            "Microcontrôleurs": "Aucune expérience",
            "Langages": "Aucun (notions Python via formation en ligne)",
            "RTOS": "Aucune",
            "Certifications": "Aucune logicielle",
            "Protocoles": "Aucun",
        },
        "formation": "Diplôme d'Ingénieur Mécanique — Arts et Métiers ParisTech (2021)",
        "projets": [
            "Conception aile composite Airbus A350 (CATIA)",
            "Calcul structure fatigue matériaux",
        ],
        "langues": "Français (natif), Anglais (C1), Arabe (natif)",
        "notes_rh": "- Profil mécanique pur, zéro compétence logicielle embarquée\n- Reconversion sans preuve de formation embarquée\n- CATIA ≠ développement firmware\n- Hors cible totale malgré contexte aéronautique",
    },

    {
        "nom": "Théo Lambert",
        "email": "theo.lambert@email.com",
        "tel": "+33 6 77 88 99 00",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 38,
        "groupe": "insuffisant",
        "accroche": "Étudiant en école d'ingénieur électronique, 1ère expérience en embarqué académique.",
        "experience": [
            ("2024 (4 mois)", "Stagiaire R&D — Laboratoire LAAS-CNRS, Toulouse",
             "Prototype robotique avec Raspberry Pi et capteurs ultrasoniques. Environnement recherche."),
        ],
        "competences": {
            "Microcontrôleurs": "Raspberry Pi 4, STM32F0 (TP uniquement)",
            "Langages": "C (basique), Python",
            "RTOS": "Aucune expérience réelle",
            "Certifications": "Aucune",
            "Protocoles": "I2C (TP), GPIO",
        },
        "formation": "3ème année École d'Ingénieur Électronique — INSA Toulouse (en cours, 2022-2025)",
        "projets": [
            "Robot éviteur d'obstacles (Raspberry Pi + ultrason)",
            "Afficheur 7 segments sur STM32 (TP)",
        ],
        "langues": "Français (natif), Anglais (B2)",
        "notes_rh": "- Pas encore diplômé, formation en cours\n- STM32 uniquement en TP, pas en production\n- Aucune expérience industrielle ou aéronautique\n- FreeRTOS, MISRA-C, DO-178C absents",
    },

    {
        "nom": "Sara Khlifi",
        "email": "sara.khlifi@email.com",
        "tel": "+33 6 88 99 00 11",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 32,
        "groupe": "insuffisant",
        "accroche": "Ingénieure qualité logicielle avec notions de développement C embarqué.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieure qualité logicielle — Alstom Transport, Saint-Ouen",
             "Tests et validation logiciel ferroviaire (SIL3). Rédaction de plans de tests. Pas de dev."),
        ],
        "competences": {
            "Microcontrôleurs": "Aucune expérience de développement",
            "Langages": "Aucun (lecture de code C uniquement)",
            "RTOS": "Connaissances théoriques SIL3 uniquement",
            "Certifications": "IEC 62279 (validation uniquement)",
            "Protocoles": "MVB ferroviaire (validation uniquement)",
        },
        "formation": "Master Qualité Logicielle — CNAM Paris (2022)",
        "projets": [
            "Plan de tests SIL3 pour système de signalisation",
            "Rédaction documentation qualification IEC 62279",
        ],
        "langues": "Français (natif), Anglais (B2), Arabe (C1)",
        "notes_rh": "- Qualité/validation ≠ développement firmware\n- Aucune compétence de développement bas niveau\n- Ferroviaire ≠ aéronautique (DO-178C absent)\n- Profil test sans capacité de développement",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GROUPE 2 : LIMITES (score 45-64) — 7 CVs → Liste attente
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "nom": "Camille Renard",
        "email": "camille.renard@email.com",
        "tel": "+33 6 99 00 11 22",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 58,
        "groupe": "limite",
        "accroche": "Ingénieure systèmes embarqués automotive avec 4 ans d'expérience en développement AUTOSAR.",
        "experience": [
            ("2021-2025 (4 ans)", "Ingénieure Embarquée — Continental Automotive, Toulouse",
             "Développement BSW AUTOSAR sur microcontrôleurs TriCore Aurix. Protocoles CAN/LIN/Ethernet."),
            ("2021 (6 mois)", "Stagiaire — Valeo Vision Systems, Paris",
             "Développement driver caméra embarquée sur ARM Cortex-M4."),
        ],
        "competences": {
            "Microcontrôleurs": "TriCore Aurix TC397, ARM Cortex-M4",
            "Langages": "C MISRA-C:2012, Ada (notions)",
            "RTOS": "OS AUTOSAR (Automotive), pas FreeRTOS safety-critical",
            "Certifications": "ASPICE Level 2 (automotive)",
            "Protocoles": "CAN, LIN, Ethernet Automotive, FlexRay",
        },
        "formation": "Diplôme d'Ingénieur Systèmes Embarqués — ENSEEIHT, Toulouse (2021)",
        "projets": [
            "Stack BSW AUTOSAR pour calculateur moteur TriCore",
            "Driver CAN-FD sur Aurix TC387",
        ],
        "langues": "Français (natif), Anglais (C1), Allemand (B1)",
        "notes_rh": "+ AUTOSAR et protocoles CAN/LIN solides — bonne base embarqué\n+ 4 ans en production automotive Tier1 (Continental)\n- Aucune expérience aéronautique — secteur critique très différent\n- DO-178C et normes sécurité aéronautique totalement absents\n- Transition automobile vers aéronautique non démontrée",
    },

    {
        "nom": "Mehdi Aouad",
        "email": "mehdi.aouad@email.com",
        "tel": "+33 6 00 11 22 33",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 52,
        "groupe": "limite",
        "accroche": "Développeur firmware IoT et Edge computing avec 3 ans d'expérience sur systèmes Zephyr.",
        "experience": [
            ("2022-2025 (3 ans)", "Développeur Firmware — Startup EdgeAI, Grenoble",
             "Firmware sur Zephyr RTOS pour capteurs industriels connectés. Protocoles BLE/LoRa/MQTT."),
        ],
        "competences": {
            "Microcontrôleurs": "nRF52840, ESP32-S3, STM32L4 (IoT grade)",
            "Langages": "C (Zephyr), Python",
            "RTOS": "Zephyr RTOS (IoT, pas safety-critical)",
            "Certifications": "Aucune certification normative",
            "Protocoles": "BLE, LoRaWAN, MQTT, USB",
        },
        "formation": "Master IoT & Systèmes Embarqués — Grenoble INP (2022)",
        "projets": [
            "Gateway LoRa/BLE pour monitoring industriel sur Zephyr",
            "Firmware capteur de vibration IIoT basse consommation",
        ],
        "langues": "Français (natif), Arabe (natif), Anglais (B2)",
        "notes_rh": "- Contexte IoT/Edge trop éloigné de l'embarqué critique aéronautique\n- RTOS Zephyr uniquement — aucune expérience FreeRTOS en safety-critical\n- Aucune certification (DO-178C, MISRA-C absents)\n- ESP32 et microcontrôleurs grand public vs STM32H7 industriel\n+ Bonne maîtrise C embarqué et protocoles communication\n+ Expérience protocoles industriels (non pertinent ici)",
    },

    {
        "nom": "Julie Marchand",
        "email": "julie.marchand@email.com",
        "tel": "+33 6 11 22 33 45",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 60,
        "groupe": "limite",
        "accroche": "Ingénieure embarquée défense avec 4 ans sur systèmes temps réel VxWorks et ARINC 429.",
        "experience": [
            ("2021-2025 (4 ans)", "Ingénieure Logiciel Embarqué — Naval Group, Cherbourg",
             "Développement C sur VxWorks pour systèmes de navigation navale. Protocoles ARINC 429/MIL-STD."),
        ],
        "competences": {
            "Microcontrôleurs": "PowerPC, ARM Cortex-A (embarqué défense)",
            "Langages": "C, Ada",
            "RTOS": "VxWorks (temps réel, mais pas FreeRTOS)",
            "Certifications": "ARINC 429 (connaissance), pas DO-178C",
            "Protocoles": "ARINC 429, MIL-STD-1553, Ethernet",
        },
        "formation": "Diplôme d'Ingénieur — École Navale Brest (2021)",
        "projets": [
            "Système de navigation inertielle sur VxWorks",
            "Bus MIL-STD-1553 pour communication sous-marine",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ Expérience systèmes temps réel critique (défense/naval)\n+ ARINC 429 — proche du domaine aéronautique\n+ 4 ans en développement C sur systèmes temps réel\n- VxWorks ≠ FreeRTOS — courbe d'apprentissage\n- DO-178C absente — certification aéronautique requise\n- STM32H7 non mentionné",
    },

    {
        "nom": "Romain Gauthier",
        "email": "romain.gauthier@email.com",
        "tel": "+33 6 22 33 44 56",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 55,
        "groupe": "limite",
        "accroche": "Développeur firmware spatial sur FPGA et microcontrôleurs avec 3 ans d'expérience.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieur Embarqué — Airbus Defence & Space, Toulouse",
             "Firmware FPGA Xilinx pour satellites de communication. Protocoles SpaceWire/MIL-STD."),
        ],
        "competences": {
            "Microcontrôleurs": "FPGA Xilinx Zynq, LEON3 (spatial)",
            "Langages": "VHDL, C (RTEMS)",
            "RTOS": "RTEMS (spatial, proche safety-critical)",
            "Certifications": "ECSS-E-ST-40 (spatial, pas DO-178C)",
            "Protocoles": "SpaceWire, MIL-STD-1553, CAN",
        },
        "formation": "Master Systèmes Embarqués Critiques — ISAE-SUPAERO (2022)",
        "projets": [
            "Firmware de contrôle d'attitude satellite sur LEON3",
            "Interface SpaceWire sur FPGA Xilinx",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ RTEMS et expérience safety-critical (spatial)\n+ Protocoles industriels (CAN, MIL-STD)\n+ Contexte critique réel (Airbus Defence)\n- FPGA/VHDL ≠ STM32 (profil différent du poste)\n- DO-178C absente (ECSS différent)\n- FreeRTOS non mentionné",
    },

    {
        "nom": "Amira Benali",
        "email": "amira.benali@email.com",
        "tel": "+33 6 33 44 55 67",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 48,
        "groupe": "limite",
        "accroche": "Ingénieure électronique embarquée ferroviaire avec 3 ans sur systèmes SIL4.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieure Logiciel Embarqué — Alstom Transport, Villeurbanne",
             "Développement C sur PPC pour systèmes de contrôle ferroviaire SIL4. IEC 62280."),
        ],
        "competences": {
            "Microcontrôleurs": "PowerPC MPC5xxx (ferroviaire)",
            "Langages": "C (MISRA-C:2004), LabVIEW",
            "RTOS": "OS propriétaire SIL4 (pas FreeRTOS)",
            "Certifications": "IEC 62280 SIL4 (ferroviaire)",
            "Protocoles": "MVB, WTB (ferroviaire uniquement)",
        },
        "formation": "Master Systèmes Embarqués Sûreté — INSA Lyon (2022)",
        "projets": [
            "Calcul de freinage SIL4 sur PowerPC",
            "Intégration HIL pour validation système ferroviaire",
        ],
        "langues": "Français (natif), Arabe (natif), Anglais (B2)",
        "notes_rh": "+ Expérience sûreté-critical réelle (SIL4)\n+ MISRA-C maîtrisé en contexte industriel\n- Ferroviaire ≠ aéronautique (normes très différentes)\n- DO-178C absente, STM32H7 non mentionné\n- FreeRTOS absent, OS propriétaire ferroviaire",
    },

    {
        "nom": "Lucas Petit",
        "email": "lucas.petit@email.com",
        "tel": "+33 6 44 55 66 78",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 62,
        "groupe": "limite",
        "accroche": "Ingénieur embarqué médical avec 4 ans sur dispositifs certifiés IEC 62304.",
        "experience": [
            ("2021-2025 (4 ans)", "Développeur Firmware — Sophysa (dispositifs médicaux), Orsay",
             "Firmware C sur ARM Cortex-M3 pour implants actifs. Certification IEC 62304 classe C."),
        ],
        "competences": {
            "Microcontrôleurs": "ARM Cortex-M3, STM32L1 (médical basse conso)",
            "Langages": "C (MISRA-C:2012), assembly ARM",
            "RTOS": "FreeRTOS (médical, pas aéronautique)",
            "Certifications": "IEC 62304 Classe C (médical)",
            "Protocoles": "I2C, SPI, UART, USB (médical)",
        },
        "formation": "Diplôme d'Ingénieur Électronique — ECE Paris (2021)",
        "projets": [
            "Firmware implant actif cardiaque ARM Cortex-M3",
            "Protocole de communication chiffré dispositif médical",
        ],
        "langues": "Français (natif), Anglais (B2)",
        "notes_rh": "+ FreeRTOS maîtrisé en contexte certifié\n+ MISRA-C:2012 appliqué en production réelle\n+ STM32 famille maîtrisée (L1, proche H7)\n- IEC 62304 ≠ DO-178C (normes différentes)\n- Médical basse conso ≠ aéronautique haute performance\n- DO-178C et protocoles CAN/JTAG aéronautiques absents",
    },

    {
        "nom": "Fatima Zahra El Idrissi",
        "email": "fz.elidrissi@email.com",
        "tel": "+33 6 55 66 77 89",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 57,
        "groupe": "limite",
        "accroche": "Ingénieure électronique embarquée 3 ans d'expérience en systèmes automobiles AUTOSAR.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieure Firmware — Faurecia/Forvia, Brières-les-Scellés",
             "Développement ASW AUTOSAR sur ECU confort. Protocoles LIN/CAN. Tests HIL."),
        ],
        "competences": {
            "Microcontrôleurs": "Renesas RH850, ARM Cortex-M7",
            "Langages": "C, MATLAB/Simulink (génération code)",
            "RTOS": "AUTOSAR OS (automotive)",
            "Certifications": "ISO 26262 ASIL-B (automotive)",
            "Protocoles": "CAN, LIN, K-Line",
        },
        "formation": "Diplôme d'Ingénieur Électronique — ENSEIRB-MATMECA, Bordeaux (2022)",
        "projets": [
            "ECU siège chauffant/ventilé AUTOSAR RH850",
            "Mise en conformité ISO 26262 ASIL-B ECU confort",
        ],
        "langues": "Français (C2), Arabe (natif), Anglais (B2)",
        "notes_rh": "+ MISRA-C et certification normative (ISO 26262)\n+ Renesas RH850 et ARM Cortex-M7 — microcontrôleurs professionnels\n- Automotive confort ≠ aéronautique critique\n- DO-178C absente, FreeRTOS non mentionné\n- AUTOSAR OS ≠ FreeRTOS (différent)",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GROUPE 3 : BONS (score 65-82) — 10 CVs → Entretien
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "nom": "Thomas Mercier",
        "email": "thomas.mercier@email.com",
        "tel": "+33 6 66 77 88 90",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 75,
        "groupe": "bon",
        "accroche": "Ingénieur systèmes embarqués 3 ans sur STM32 et FreeRTOS en contexte industriel aéronautique.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieur Logiciel Embarqué — Safran Electronics & Defense, Massy",
             "Développement firmware STM32H7 pour centrales inertielles. FreeRTOS, MISRA-C. Audit MISRA réussi."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F4 (production industrielle)",
            "Langages": "C (MISRA-C:2012 strict), assembly ARM",
            "RTOS": "FreeRTOS (contexte industriel, pas DO-178C)",
            "Certifications": "Audit MISRA-C réussi (Safran)",
            "Protocoles": "SPI, I2C, CAN, UART, Segger J-Link",
        },
        "formation": "Diplôme d'Ingénieur Systèmes Embarqués — ISAE-SUPAERO, Toulouse (2022)",
        "projets": [
            "Firmware centrale inertielle STM32H7 + FreeRTOS (Safran)",
            "Driver SPI haute vitesse pour capteur MEMS",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ STM32H7 utilisé en production embarquée réelle (pas académique)\n+ FreeRTOS intégré avec gestion préemptive confirmée\n+ Audit MISRA-C réussi sur projet industriel\n- DO-178C absent — pas encore certifié aéronautique\n- 3 ans d'expérience (minimum requis mais juste)",
    },

    {
        "nom": "Alexandre Dubois",
        "email": "alexandre.dubois@email.com",
        "tel": "+33 6 77 88 99 01",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 72,
        "groupe": "bon",
        "accroche": "Ingénieur embarqué aéronautique 4 ans sur systèmes temps réel FreeRTOS et protocoles ARINC.",
        "experience": [
            ("2021-2025 (4 ans)", "Développeur Firmware — Dassault Aviation, Saint-Cloud",
             "Firmware C sur ARM Cortex-M7 pour avionique Falcon. FreeRTOS, protocoles ARINC 429."),
        ],
        "competences": {
            "Microcontrôleurs": "ARM Cortex-M7 (STM32H7 compatible), NXP i.MX RT",
            "Langages": "C (MISRA-C:2012), assembly",
            "RTOS": "FreeRTOS (aéronautique)",
            "Certifications": "Formation DO-178C (niveau B en cours)",
            "Protocoles": "ARINC 429, CAN, SPI, JTAG",
        },
        "formation": "Diplôme d'Ingénieur Électronique — CentraleSupélec (2021)",
        "projets": [
            "Driver ARINC 429 sur ARM Cortex-M7 pour avionique Falcon",
            "Intégration FreeRTOS multi-tâches temps réel dur",
        ],
        "langues": "Français (natif), Anglais (C2)",
        "notes_rh": "+ FreeRTOS en contexte aéronautique réel\n+ Protocoles ARINC 429 maîtrisés\n+ 4 ans en développement aéronautique\n- DO-178C en cours (pas encore certifié)\n- STM32H7 non directement mentionné (Cortex-M7 compatible)",
    },

    {
        "nom": "Céline Dupont",
        "email": "celine.dupont@email.com",
        "tel": "+33 6 88 99 00 12",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 78,
        "groupe": "bon",
        "accroche": "Ingénieure systèmes embarqués 5 ans sur STM32 et FreeRTOS, spécialisée capteurs inertiels.",
        "experience": [
            ("2020-2025 (5 ans)", "Ingénieure Embarquée — Thales Avionics, Bordeaux",
             "Développement C/MISRA sur STM32F7 pour FMS (Flight Management System). FreeRTOS, JTAG."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32F7, STM32H7 (avionique)",
            "Langages": "C (MISRA-C:2012), Python (tests)",
            "RTOS": "FreeRTOS (avionique, connaissance DO-178C niveau B)",
            "Certifications": "Connaissance DO-178C DAL-B (non certifiée auteur)",
            "Protocoles": "ARINC 429, CAN, SPI, I2C, JTAG/SWD",
        },
        "formation": "Diplôme d'Ingénieur — École Polytechnique Nantes (2020)",
        "projets": [
            "Module FMS STM32F7 avec FreeRTOS pour Thales (avionique)",
            "Qualification DO-178C niveau B sur module navigation",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ STM32H7 maîtrisé en contexte avionique\n+ FreeRTOS avec connaissance DO-178C\n+ 5 ans chez Thales — contexte identique au poste\n- Non certifiée en tant qu'auteur DO-178C (connaissance technicienne)\n- MISRA-C validé en production",
    },

    {
        "nom": "Kevin Morin",
        "email": "kevin.morin@email.com",
        "tel": "+33 6 99 00 11 23",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 68,
        "groupe": "bon",
        "accroche": "Ingénieur embarqué 4 ans sur microcontrôleurs ARM en contexte défense et sécurité.",
        "experience": [
            ("2021-2025 (4 ans)", "Développeur Firmware — MBDA, Vélizy",
             "Développement C embarqué sur ARM Cortex-M4 pour systèmes de guidage. FreeRTOS, temps réel strict."),
        ],
        "competences": {
            "Microcontrôleurs": "ARM Cortex-M4 (STM32F4), Cortex-M7",
            "Langages": "C (MISRA-C:2004), C++ (limité)",
            "RTOS": "FreeRTOS (défense, safety-critical)",
            "Certifications": "Connaissance DO-178C (formation interne MBDA)",
            "Protocoles": "CAN, SPI, UART, JTAG",
        },
        "formation": "Diplôme d'Ingénieur — ENSIIE Évry (2021)",
        "projets": [
            "Système guidage temps réel ARM Cortex-M4 + FreeRTOS",
            "Driver CAN haute priorité pour bus avionique",
        ],
        "langues": "Français (natif), Anglais (B2)",
        "notes_rh": "+ FreeRTOS maîtrisé en contexte safety-critical défense\n+ Protocoles CAN et JTAG — identiques au poste\n+ Formation DO-178C interne MBDA\n- STM32H7 (H-series) non directement mentionné\n- MISRA-C version 2004 (2012 préféré)",
    },

    {
        "nom": "Marion Lefebvre",
        "email": "marion.lefebvre@email.com",
        "tel": "+33 6 00 11 22 34",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 70,
        "groupe": "bon",
        "accroche": "Ingénieure avionique embarquée 4 ans sur systèmes certifiés DO-178C niveau C.",
        "experience": [
            ("2021-2025 (4 ans)", "Ingénieure Logiciel Embarqué — Collins Aerospace, Blagnac",
             "Développement et qualification DO-178C DAL-C sur display avionique. FreeRTOS, ARM."),
        ],
        "competences": {
            "Microcontrôleurs": "ARM Cortex-A (display), ARM Cortex-M (périphériques)",
            "Langages": "C, Ada (avionique)",
            "RTOS": "FreeRTOS (qualifié DAL-C)",
            "Certifications": "DO-178C DAL-C (auteur, Collins Aerospace)",
            "Protocoles": "ARINC 429, ARINC 664, MIL-STD",
        },
        "formation": "Diplôme d'Ingénieur Aéronautique — ENAC Toulouse (2021)",
        "projets": [
            "Qualification DO-178C DAL-C display avionique A320neo",
            "Middleware ARINC 664 (AFDX) sur ARM",
        ],
        "langues": "Français (natif), Anglais (C2)",
        "notes_rh": "+ DO-178C DAL-C certifiée en tant qu'auteur\n+ FreeRTOS qualifié en contexte avionique\n+ 4 ans Collins Aerospace — industrie identique\n- DAL-C (le poste demande DAL-B ou supérieur)\n- STM32H7 non directement mentionné",
    },

    {
        "nom": "Nicolas Bernard",
        "email": "nicolas.bernard@email.com",
        "tel": "+33 6 11 22 33 46",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 74,
        "groupe": "bon",
        "accroche": "Ingénieur firmware 5 ans sur STM32 en contexte industriel et médical certifié.",
        "experience": [
            ("2020-2025 (5 ans)", "Lead Firmware — Microdem, Grenoble",
             "Lead développement firmware STM32H7 pour équipements médicaux implantables IEC 62304 classe C."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F7, STM32L4 (production série)",
            "Langages": "C (MISRA-C:2012), assembly ARM Cortex-M",
            "RTOS": "FreeRTOS (certifié IEC 62304 — proche DO-178C)",
            "Certifications": "IEC 62304 Classe C (lead développeur)",
            "Protocoles": "SPI, I2C, CAN, USB, BLE, JTAG",
        },
        "formation": "Diplôme d'Ingénieur Électronique — Phelma Grenoble INP (2020)",
        "projets": [
            "Firmware STM32H7 implant cardiaque IEC 62304 Classe C",
            "Driver SPI 20MHz pour capteur pression haute précision",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ STM32H7 en production série — microcontrôleur exact du poste\n+ MISRA-C:2012 appliqué comme lead dev\n+ FreeRTOS certifié (IEC 62304 ≈ DO-178C niveau process)\n- IEC 62304 ≠ DO-178C (différent, mais procédure proche)\n- Pas de contexte aéronautique direct\n- 5 ans d'expérience solide",
    },

    {
        "nom": "Antoine Simon",
        "email": "antoine.simon@email.com",
        "tel": "+33 6 22 33 44 57",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 80,
        "groupe": "bon",
        "accroche": "Ingénieur embarqué aéronautique 5 ans Airbus, spécialiste STM32 FreeRTOS et certifications.",
        "experience": [
            ("2020-2025 (5 ans)", "Ingénieur Logiciel Embarqué — Airbus Operations, Toulouse",
             "Firmware C sur STM32H7 pour systèmes de test avionique. FreeRTOS, MISRA-C. Formation DO-178C interne."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F7 (avionique Airbus)",
            "Langages": "C (MISRA-C:2012), Python (tests/CI)",
            "RTOS": "FreeRTOS (avionique, formation DO-178C Airbus)",
            "Certifications": "Formation DO-178C DAL-B (Airbus, pas auteur)",
            "Protocoles": "CAN, ARINC 429, SPI, JTAG/SWD, Ethernet",
        },
        "formation": "Diplôme d'Ingénieur — ENSEEIHT Toulouse (2020)",
        "projets": [
            "Banc de test avionique STM32H7 FreeRTOS (Airbus A350)",
            "Bridge CAN-Ethernet embarqué pour validation système",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ STM32H7 en production Airbus — contexte avionique direct\n+ FreeRTOS avec formation DO-178C Airbus\n+ MISRA-C:2012 validé en production\n+ Protocoles identiques au poste (CAN, ARINC, JTAG)\n- Formation DO-178C mais pas auteur certifié\n- Test et validation ≠ développement produit série",
    },

    {
        "nom": "Karim Hassani",
        "email": "karim.hassani@email.com",
        "tel": "+33 6 33 44 55 68",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 82,
        "groupe": "bon",
        "accroche": "Ingénieur embarqué 6 ans sur microcontrôleurs ARM en contexte aéronautique et spatial.",
        "experience": [
            ("2019-2025 (6 ans)", "Ingénieur Logiciel Embarqué — Airbus Defence & Space, Toulouse",
             "Firmware C/MISRA sur STM32H7 pour systèmes embarqués satellites. FreeRTOS, JTAG, protocoles critiques."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F4, LEON3 (spatial)",
            "Langages": "C (MISRA-C:2012), assembly ARM, Python",
            "RTOS": "FreeRTOS + RTEMS (double compétence)",
            "Certifications": "ECSS-E-ST-40 + formation DO-178C interne",
            "Protocoles": "CAN, SPI, UART, SpaceWire, JTAG/SWD",
        },
        "formation": "Diplôme d'Ingénieur — ISAE-SUPAERO Toulouse (2019)",
        "projets": [
            "OBC (On-Board Computer) satellite STM32H7 + FreeRTOS",
            "Interface SpaceWire/CAN pour payload instrumentale",
        ],
        "langues": "Français (C2), Arabe (natif), Anglais (C1)",
        "notes_rh": "+ STM32H7 maîtrisé en contexte critique réel\n+ FreeRTOS + RTEMS — double compétence RTOS\n+ 6 ans en développement critique spatial/aéronautique\n+ MISRA-C:2012 strict en production\n- DO-178C formation uniquement (pas auteur)\n- Spatial ≠ aéronautique (normes différentes)",
    },

    {
        "nom": "Elise Fontaine",
        "email": "elise.fontaine@email.com",
        "tel": "+33 6 44 55 66 79",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 76,
        "groupe": "bon",
        "accroche": "Ingénieure systèmes embarqués 4 ans Thales, spécialiste FPGA et microcontrôleurs ARM.",
        "experience": [
            ("2021-2025 (4 ans)", "Ingénieure Embarquée — Thales SIX GTS, Gennevilliers",
             "Développement C sur ARM + FPGA pour systèmes de communication sécurisée défense. FreeRTOS."),
        ],
        "competences": {
            "Microcontrôleurs": "ARM Cortex-M7 (STM32H7), FPGA Xilinx",
            "Langages": "C (MISRA-C:2012), VHDL, Python",
            "RTOS": "FreeRTOS (défense, safety-critical)",
            "Certifications": "Connaissance DO-178C et Common Criteria",
            "Protocoles": "SPI, I2C, CAN, Ethernet, JTAG",
        },
        "formation": "Diplôme d'Ingénieur — TELECOM Paris (2021)",
        "projets": [
            "Chiffrement embarqué ARM + FPGA pour radio sécurisée Thales",
            "Driver JTAG custom pour débogage système défense",
        ],
        "langues": "Français (natif), Anglais (C2)",
        "notes_rh": "+ ARM Cortex-M7 compatible STM32H7\n+ FreeRTOS en contexte safety-critical défense\n+ MISRA-C:2012 en production Thales\n+ JTAG maîtrisé (tool chain identique)\n- Défense/communication ≠ aéronautique direct\n- DO-178C connaissance (pas auteur certifié)",
    },

    {
        "nom": "Hugo Rousseau",
        "email": "hugo.rousseau@email.com",
        "tel": "+33 6 55 66 77 90",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 67,
        "groupe": "bon",
        "accroche": "Ingénieur embarqué 4 ans en industrie manufacturière sur microcontrôleurs STM32 et FreeRTOS.",
        "experience": [
            ("2021-2025 (4 ans)", "Développeur Firmware — Schneider Electric, Grenoble",
             "Firmware STM32F7/H7 pour automates industriels IEC 61131. FreeRTOS, protocoles industriels."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F7 (industrie)",
            "Langages": "C, C++ (IEC 61131)",
            "RTOS": "FreeRTOS (industrie, pas certifié aéronautique)",
            "Certifications": "IEC 61131-3 (automation industrielle)",
            "Protocoles": "Modbus, EtherCAT, CAN, SPI, JTAG",
        },
        "formation": "Diplôme d'Ingénieur — Grenoble INP Esisar (2021)",
        "projets": [
            "PLC firmware STM32H7 FreeRTOS pour Schneider Modicon",
            "Stack EtherCAT temps réel sur ARM Cortex-M7",
        ],
        "langues": "Français (natif), Anglais (B2)",
        "notes_rh": "+ STM32H7 en production industrielle réelle\n+ FreeRTOS maîtrisé sur microcontrôleur exact du poste\n+ Protocoles industriels CAN maîtrisés\n- Industrie/automation ≠ aéronautique critique\n- DO-178C et MISRA-C absents\n- Normes aéronautiques non maîtrisées",
    },

    # ═══════════════════════════════════════════════════════════════════════════
    # GROUPE 4 : EXCELLENTS (score 83-95) — 5 CVs → Entretien prioritaire
    # ═══════════════════════════════════════════════════════════════════════════

    {
        "nom": "Pierre-Henri Leconte",
        "email": "ph.leconte@email.com",
        "tel": "+33 6 66 77 88 91",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 92,
        "groupe": "excellent",
        "accroche": "Ingénieur systèmes embarqués senior 7 ans, certifié DO-178C DAL-B chez Thales Avionics.",
        "experience": [
            ("2018-2025 (7 ans)", "Ingénieur Senior Logiciel Embarqué — Thales Avionics, Bordeaux",
             "Lead développeur firmware STM32H7 pour FMS avionique. DO-178C DAL-B. FreeRTOS. Segger JTAG."),
            ("2018 (6 mois)", "Ingénieur embarqué — Thales Systèmes Aéroportés, Elancourt",
             "Intégration firmware avionique C/MISRA sur ARM Cortex-M7. Formation DO-178C."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7 (production série avionique), ARM Cortex-M7",
            "Langages": "C (MISRA-C:2012 strict), assembly ARM, Python (CI/CD)",
            "RTOS": "FreeRTOS (qualifié DO-178C DAL-B)",
            "Certifications": "DO-178C DAL-B auteur (Thales), formation RTCA",
            "Protocoles": "ARINC 429, CAN, SPI, I2C, JTAG/SWD Segger",
        },
        "formation": "Diplôme d'Ingénieur — ISAE-SUPAERO Toulouse (2018) | Option Avionique",
        "projets": [
            "FMS STM32H7 + FreeRTOS DO-178C DAL-B (Thales A320neo/A350)",
            "Driver ARINC 429 qualifié DO-178C pour bus avionique",
            "Lead qualification 50 000 lignes de code DAL-B",
        ],
        "langues": "Français (natif), Anglais (C2), Espagnol (B1)",
        "notes_rh": "+ DO-178C DAL-B validé chez Thales Avionics — certification industrielle réelle\n+ 7 ans en contexte embarqué critique aéronautique\n+ STM32H7 déployé en production série certifiée\n+ Segger J-Link et chaîne debug professionnelle maîtrisée\n- Pas de mention AUTOSAR (non bloquant pour ce poste)",
    },

    {
        "nom": "Sarah Fontaine",
        "email": "sarah.fontaine@email.com",
        "tel": "+33 6 77 88 99 02",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 88,
        "groupe": "excellent",
        "accroche": "Ingénieure embarquée 5 ans Safran, certifiée DO-178C DAL-B sur STM32H7 et FreeRTOS.",
        "experience": [
            ("2020-2025 (5 ans)", "Ingénieure Logiciel Embarqué — Safran Electronics & Defense, Massy",
             "Développement et qualification DO-178C DAL-B firmware STM32H7 pour UAV et drones défense. FreeRTOS."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F7 (production certifiée)",
            "Langages": "C (MISRA-C:2012 strict), Python (tests), assembly",
            "RTOS": "FreeRTOS (certifié DO-178C DAL-B, Safran)",
            "Certifications": "DO-178C DAL-B auteur (Safran Electronics & Defense)",
            "Protocoles": "CAN, SPI, I2C, UART, JTAG/SWD, ARINC 429",
        },
        "formation": "Diplôme d'Ingénieur Aéronautique — ENAC Toulouse (2020)",
        "projets": [
            "Firmware UAV STM32H7 + FreeRTOS DO-178C DAL-B (Safran)",
            "Stack CAN temps réel pour capteurs inertiels drones défense",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ DO-178C DAL-B chez Safran — équivalent Thales, même niveau criticité\n+ FreeRTOS en contexte sécurité-critique confirmé production\n+ MISRA-C strict appliqué sur chaîne de compilation certifiée\n+ STM32H7 déployé — même hardware que l'offre\n- 5 ans (légèrement moins que Pierre-Henri mais largement suffisant)",
    },

    {
        "nom": "Julien Moreau",
        "email": "julien.moreau@email.com",
        "tel": "+33 6 88 99 00 13",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 90,
        "groupe": "excellent",
        "accroche": "Ingénieur embarqué senior 8 ans, expert FreeRTOS/DO-178C chez Airbus et Safran.",
        "experience": [
            ("2022-2025 (3 ans)", "Lead Ingénieur Embarqué — Airbus Operations, Toulouse",
             "Lead dev firmware STM32H7 + FreeRTOS pour système commande de vol. DO-178C DAL-A."),
            ("2017-2022 (5 ans)", "Ingénieur Logiciel Embarqué — Safran Landing Systems, Vélizy",
             "Firmware ARM Cortex-M7 pour train d'atterrissage. DO-178C DAL-B. MISRA-C:2012."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, ARM Cortex-M7/A (avionique)",
            "Langages": "C (MISRA-C:2012), Ada (commande de vol), Python",
            "RTOS": "FreeRTOS (certifié DO-178C DAL-A et DAL-B)",
            "Certifications": "DO-178C DAL-A (auteur, Airbus) + DAL-B (Safran)",
            "Protocoles": "ARINC 429, CAN, SPI, JTAG Segger, Ethernet avionique",
        },
        "formation": "Diplôme d'Ingénieur — École Polytechnique (2017) | Spécialité Systèmes Critiques",
        "projets": [
            "Commande de vol primaire STM32H7 DO-178C DAL-A (Airbus A380)",
            "Train atterrissage DO-178C DAL-B Safran — 80 000 lignes qualifiées",
        ],
        "langues": "Français (natif), Anglais (C2), Allemand (B2)",
        "notes_rh": "+ DO-178C DAL-A ET DAL-B — double certification rare\n+ 8 ans en développement embarqué critique aéronautique\n+ Lead développeur Airbus commandes de vol\n+ STM32H7 et FreeRTOS certifiés en production\n- Profil très senior, salaire probablement au-dessus de la fourchette",
    },

    {
        "nom": "Yasmine Bouri",
        "email": "yasmine.bouri@email.com",
        "tel": "+33 6 99 00 11 24",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 40,
        "groupe": "insuffisant",
        "accroche": "Jeune ingénieure systèmes embarqués Master, passionnée par l'embarqué temps réel et l'automatisation.",
        "experience": [
            ("2024 (5 mois)", "Stagiaire Ingénieure Embarquée — Société Générale IT, Paris",
             "Développement scripts Python pour automatisation tests. Pas d'embarqué réel."),
            ("2023 (3 mois)", "Stagiaire — Startup RoboticLabs, Toulouse",
             "Prototype robot avec STM32CubeIDE et capteurs RGB. Environnement académique."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32 (STM32CubeIDE, niveau académique), Arduino",
            "Langages": "C (notions embarquées), Python",
            "RTOS": "FreeRTOS superficiel (TP university)",
            "Certifications": "Aucune",
            "Protocoles": "UART (basique)",
        },
        "formation": "Master Systèmes Embarqués — Université Paul Sabatier Toulouse (2024)",
        "projets": [
            "Robot suiveur de ligne (projet académique, STM32CubeIDE)",
            "Affichage temps réel FreeRTOS (TP Master)",
        ],
        "langues": "Français (C1), Arabe (natif), Anglais (B1 technique)",
        "notes_rh": "- Aucune expérience industrielle réelle (stages académiques uniquement)\n- STM32 uniquement en TP, pas en production\n- FreeRTOS superficiel via TP universitaire\n- DO-178C, MISRA-C, protocoles industriels absents\n- Poste demande minimum 3 ans d'expérience industrielle",
    },

    {
        "nom": "Marc Lefebvre",
        "email": "marc.lefebvre@email.com",
        "tel": "+33 6 00 11 22 35",
        "poste": "Ingénieur Systèmes Embarqués",
        "score_attendu": 85,
        "groupe": "excellent",
        "accroche": "Ingénieur embarqué 6 ans chez Thales et Safran, expert STM32H7/FreeRTOS/DO-178C.",
        "experience": [
            ("2022-2025 (3 ans)", "Ingénieur Senior Embarqué — Safran Nacelles, Gonfreville",
             "Firmware STM32H7 pour FADEC (Full Authority Digital Engine Control). DO-178C DAL-B."),
            ("2019-2022 (3 ans)", "Ingénieur Logiciel — Thales Avionics, Bordeaux",
             "Développement C/MISRA embarqué pour affichage avionique. FreeRTOS. Segger JTAG."),
        ],
        "competences": {
            "Microcontrôleurs": "STM32H7, STM32F4 (production avionique/moteur)",
            "Langages": "C (MISRA-C:2012), assembly ARM Cortex-M7",
            "RTOS": "FreeRTOS (qualifié DO-178C DAL-B)",
            "Certifications": "DO-178C DAL-B auteur (Safran Nacelles)",
            "Protocoles": "ARINC 429, CAN, SPI, JTAG Segger, RS-422",
        },
        "formation": "Diplôme d'Ingénieur — ENSEEIHT Toulouse (2019) | Option Électronique Embarquée",
        "projets": [
            "FADEC STM32H7 DO-178C DAL-B — contrôle moteur CFM LEAP",
            "Display avionique FreeRTOS + ARINC 429 (Thales)",
        ],
        "langues": "Français (natif), Anglais (C1)",
        "notes_rh": "+ DO-178C DAL-B auteur chez Safran (moteur aéronautique)\n+ STM32H7 en FADEC — contexte critique identique au poste\n+ 6 ans Thales + Safran — double expérience industrielle\n+ FreeRTOS et ARINC 429 maîtrisés en production\n- Profil FADEC (moteur) vs avionique (légèrement différent)",
    },
]


# ── Génération PDF ────────────────────────────────────────────────────────────

def make_styles():
    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        'Name', parent=styles['Normal'],
        fontSize=22, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a2e'),
        spaceAfter=2,
    )
    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica',
        textColor=colors.HexColor('#4a4a8a'),
        spaceAfter=4,
    )
    section_style = ParagraphStyle(
        'Section', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c3e50'),
        spaceBefore=10, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=colors.HexColor('#333333'),
        leading=14, spaceAfter=3,
    )
    bullet_style = ParagraphStyle(
        'Bullet', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=colors.HexColor('#333333'),
        leading=13, leftIndent=10, spaceAfter=2,
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#4a4a8a'),
    )
    return name_style, title_style, section_style, body_style, bullet_style, label_style


def section_header(title, section_style):
    return [
        Paragraph(title.upper(), section_style),
        HRFlowable(width="100%", thickness=1.2,
                   color=colors.HexColor('#4a4a8a'), spaceAfter=5),
    ]


def generate_cv_pdf(candidat, filepath):
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    name_style, title_style, section_style, body_style, bullet_style, label_style = make_styles()
    story = []

    # ── En-tête ───────────────────────────────────────────────────────────────
    story.append(Paragraph(candidat["nom"], name_style))
    story.append(Paragraph(candidat["poste"], title_style))

    contact_data = [[
        Paragraph(f"✉ {candidat['email']}", body_style),
        Paragraph(f"📞 {candidat['tel']}", body_style),
        Paragraph(f"📍 France", body_style),
    ]]
    contact_table = Table(contact_data, colWidths=[6*cm, 5*cm, 5.5*cm])
    contact_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(contact_table)
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#1a1a2e'), spaceAfter=8))

    # ── Accroche ─────────────────────────────────────────────────────────────
    story.append(Paragraph(candidat["accroche"], ParagraphStyle(
        'Accroche', fontSize=9.5, fontName='Helvetica',
        textColor=colors.HexColor('#555555'),
        leading=15, spaceAfter=8,
    )))

    # ── Expérience ────────────────────────────────────────────────────────────
    story.extend(section_header("Expérience Professionnelle", section_style))
    for periode, poste, desc in candidat["experience"]:
        story.append(Paragraph(f"<b>{poste}</b>", ParagraphStyle(
            'ExpTitle', fontSize=9.5, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1a1a2e'), spaceAfter=1,
        )))
        story.append(Paragraph(periode, ParagraphStyle(
            'ExpPeriode', fontSize=8.5, fontName='Helvetica',
            textColor=colors.HexColor('#4a4a8a'), spaceAfter=2,
        )))
        story.append(Paragraph(desc, bullet_style))
        story.append(Spacer(1, 0.2*cm))

    # ── Compétences ───────────────────────────────────────────────────────────
    story.extend(section_header("Compétences Techniques", section_style))
    comp_rows = []
    for label, valeur in candidat["competences"].items():
        comp_rows.append([
            Paragraph(label, label_style),
            Paragraph(valeur, body_style),
        ])
    comp_table = Table(comp_rows, colWidths=[4.5*cm, 12*cm])
    comp_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ROWBACKGROUNDS', (0,0), (-1,-1),
         [colors.HexColor('#f8f9ff'), colors.white]),
    ]))
    story.append(comp_table)
    story.append(Spacer(1, 0.2*cm))

    # ── Formation ─────────────────────────────────────────────────────────────
    story.extend(section_header("Formation", section_style))
    story.append(Paragraph(candidat["formation"], body_style))
    story.append(Spacer(1, 0.1*cm))

    # ── Projets ───────────────────────────────────────────────────────────────
    story.extend(section_header("Projets Marquants", section_style))
    for projet in candidat["projets"]:
        story.append(Paragraph(f"• {projet}", bullet_style))

    # ── Langues ───────────────────────────────────────────────────────────────
    story.extend(section_header("Langues", section_style))
    story.append(Paragraph(candidat["langues"], body_style))

    doc.build(story)


# ── Exécution ─────────────────────────────────────────────────────────────────

def main():
    groupes = {"insuffisant": 0, "limite": 0, "bon": 0, "excellent": 0}
    generated = []

    for i, cand in enumerate(CANDIDATS, 1):
        safe_name = cand["nom"].replace(" ", "_").replace("-", "_")
        filename  = f"{i:02d}_{safe_name}_{cand['groupe'].upper()}_score{cand['score_attendu']}.pdf"
        filepath  = os.path.join(OUTPUT_DIR, filename)
        generate_cv_pdf(cand, filepath)
        groupes[cand["groupe"]] += 1
        generated.append((i, cand["nom"], cand["score_attendu"], cand["groupe"], filename))
        print(f"  [{i:02d}] {cand['nom']:<30} score={cand['score_attendu']:>2}  groupe={cand['groupe']}")

    print(f"\n{'='*65}")
    print(f"  {len(generated)} CVs générés dans ./{OUTPUT_DIR}/")
    print(f"{'='*65}")
    print(f"  Insuffisants  (20-44) : {groupes['insuffisant']} CVs → Refus")
    print(f"  Limites       (45-64) : {groupes['limite']} CVs → Liste attente")
    print(f"  Bons          (65-82) : {groupes['bon']} CVs → Entretien")
    print(f"  Excellents    (83-95) : {groupes['excellent']} CVs → Entretien prioritaire")
    print(f"{'='*65}")
    print()
    print("  Notes RH suggérées par CV :")
    print("  (à copier dans le modal +/- de MiniGED lors du traitement)")
    print()
    for i, nom, score, groupe, _ in generated:
        cand = CANDIDATS[i-1]
        print(f"  [{i:02d}] {nom} — score attendu {score}")
        for ligne in cand["notes_rh"].split("\n"):
            if ligne.strip():
                print(f"       {ligne}")
        print()


if __name__ == "__main__":
    main()
