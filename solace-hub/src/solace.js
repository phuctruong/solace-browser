(function () {
  'use strict';

  const tauri = window.__TAURI__;
  const HUB_API_BASE = 'http://localhost:8888';
  const HUB_THEME_KEY = 'solace-hub-theme';
  const HUB_FONT_KEY = 'solace-hub-font-scale';
  const HUB_LOCALE_KEY = 'solace-hub-locale';
  const HUB_LOCALES = [
    'am', 'ar', 'bg', 'bn', 'ca', 'cs', 'da', 'de', 'el', 'en', 'es', 'et',
    'fa', 'fi', 'fil', 'fr', 'ha', 'he', 'hi', 'hr', 'hu', 'id', 'it', 'ja',
    'ko', 'lt', 'lv', 'ms', 'nl', 'no', 'pl', 'pt', 'ro', 'ru', 'sk', 'sl',
    'sr', 'sv', 'sw', 'th', 'tr', 'uk', 'vi', 'yo', 'zh-hant', 'zh', 'zu'
  ];
  const RTL_LOCALES = ['ar'];
  const TRANSLATIONS = {
    en: {
      toolbar_language: 'Language',
      toolbar_theme: 'Theme',
      toolbar_text: 'Text',
      summary: 'Hub keeps localhost:8888 alive on this machine, opens Solace Browser, and keeps the first choice small and reversible.',
      open_browser: 'Open Solace Browser',
      quick_setup: 'Quick setup',
      quick_setup_title: 'Get one useful report with a reversible first step',
      step1_label: 'Choose local mode',
      step2_label: 'Connect account',
      step3_label: 'Launch Yinyang',
      progress_step: 'Step {step} of 3',
      progress_complete: 'Completed {count} / 3',
      step1_title: 'Choose one local mode first.',
      step1_copy: 'Pick one local mode now. You can change it later without losing the local setup.',
      step1_primary: 'Use BYOK',
      step1_secondary: 'Autodetect Local CLI',
      step1_notes_1: 'Use BYOK if you already have a model key and want to move fast.',
      step1_notes_2: 'Use Local CLI if Codex, Claude Code, Gemini, or Aider already live on this machine.',
      step2_title: 'Connect an account only if it helps.',
      step2_copy: 'Stay local by default. Add sync, remote control, or shared access only when the extra surface is worth it.',
      step2_primary: 'Sign In / Create Account',
      step2_secondary: 'Stay local-first',
      step2_notes_1: 'A free account lets the dashboard, Morning Brief, and optional cloud sync identify this machine only when you ask for that broader shared-state surface.',
      step2_notes_2: 'You can skip this and keep using local-first mode right now.',
      step3_title: 'Open the Browser and finish in Yinyang.',
      step3_copy: 'Run one app. Keep one report. Improve it later only if the first result earns the time.',
      step3_primary: 'Open Solace Browser',
      step3_secondary: 'Open Agent Guide',
      step3_notes_1: 'The browser opens on the real Solace AGI dashboard.',
      step3_notes_2: 'The pinned Yinyang sidebar is where apps, schedules, and automations come alive.'
    },
    es: {
      toolbar_language: 'Idioma', toolbar_theme: 'Tema', toolbar_text: 'Texto',
      summary: 'Solace Hub controla la salud local, el acceso de agentes en el puerto 8888 y el lanzamiento del navegador.',
      open_browser: 'Abrir Solace Browser', quick_setup: 'Configuracion rapida', quick_setup_title: 'Tres pasos para un asistente listo',
      step1_label: 'Elegir modo local', step2_label: 'Conectar cuenta', step3_label: 'Abrir Yinyang',
      progress_step: 'Paso {step} de 3', progress_complete: 'Completado {count} / 3',
      step1_title: 'Elige como alimentar a Yinyang.', step1_copy: 'Empieza gratis con BYOK o detecta un CLI local. Ambos caminos siguen siendo local-first.',
      step1_primary: 'Usar BYOK', step1_secondary: 'Detectar CLI local',
      step1_notes_1: 'Usa BYOK si ya tienes tu propio proveedor de modelos.', step1_notes_2: 'Usa CLI local si Codex, Claude Code, Gemini o Aider ya viven en esta maquina.',
      step2_title: 'Conecta tu cuenta de Solace AGI cuando quieras mas.', step2_copy: 'Una cuenta gratis o de pago desbloquea sincronizacion, control remoto, equipo y LLM gestionado.',
      step2_primary: 'Iniciar sesion / Crear cuenta', step2_secondary: 'Seguir local-first',
      step2_notes_1: 'Una cuenta gratis permite que el dashboard, Morning Brief y la nube sepan quien eres.', step2_notes_2: 'Puedes omitirlo y seguir en modo local-first ahora.',
      step3_title: 'Abre Solace Browser y termina dentro de Yinyang.', step3_copy: 'Cuando el navegador se abra, la barra lateral fija de Yinyang podra instalar apps, crear horarios y guiar el resto.',
      step3_primary: 'Abrir Solace Browser', step3_secondary: 'Abrir guia de agentes',
      step3_notes_1: 'El navegador se abre en el dashboard real de Solace AGI.', step3_notes_2: 'La barra lateral fija de Yinyang es donde viven apps, horarios y automatizaciones.'
    },
    vi: {
      toolbar_language: 'Ngon ngu', toolbar_theme: 'Giao dien', toolbar_text: 'Chu',
      summary: 'Solace Hub quan ly suc khoe cuc bo, truy cap agent o cong 8888 va viec mo trinh duyet.',
      open_browser: 'Mo Solace Browser', quick_setup: 'Thiet lap nhanh', quick_setup_title: 'Ba buoc de co tro ly san sang',
      step1_label: 'Chon che do local', step2_label: 'Ket noi tai khoan', step3_label: 'Mo Yinyang',
      progress_step: 'Buoc {step} / 3', progress_complete: 'Hoan tat {count} / 3',
      step1_title: 'Chon cach cap suc manh cho Yinyang.', step1_copy: 'Bat dau mien phi bang BYOK hoac tu dong tim CLI cuc bo. Ca hai van local-first.',
      step1_primary: 'Dung BYOK', step1_secondary: 'Tu dong tim CLI',
      step1_notes_1: 'Dung BYOK neu ban da co nha cung cap mo hinh rieng.', step1_notes_2: 'Dung CLI local neu Codex, Claude Code, Gemini hoac Aider da co san tren may nay.',
      step2_title: 'Ket noi tai khoan Solace AGI khi ban can nhieu hon.', step2_copy: 'Tai khoan mien phi hoac tra phi mo khoa dong bo, dieu khien tu xa, team va LLM quan ly.',
      step2_primary: 'Dang nhap / Tao tai khoan', step2_secondary: 'Van de local-first',
      step2_notes_1: 'Tai khoan mien phi giup dashboard, Morning Brief va cloud biet ban la ai.', step2_notes_2: 'Ban co the bo qua va van dung local-first ngay bay gio.',
      step3_title: 'Mo Solace Browser va hoan tat trong Yinyang.', step3_copy: 'Khi trinh duyet mo len, thanh ben Yinyang co dinh se cai app, tao lich va huong dan phan con lai.',
      step3_primary: 'Mo Solace Browser', step3_secondary: 'Mo huong dan agent',
      step3_notes_1: 'Trinh duyet mo vao dashboard that cua Solace AGI.', step3_notes_2: 'Thanh ben Yinyang co dinh la noi app, lich va tu dong hoa hoat dong.'
    },
    zh: {
      toolbar_language: '语言', toolbar_theme: '主题', toolbar_text: '文字',
      summary: 'Solace Hub 负责本地运行状态、8888 端口上的智能体访问以及浏览器启动。',
      open_browser: '打开 Solace Browser', quick_setup: '快速设置', quick_setup_title: '三步即可获得可用助手',
      step1_label: '选择本地模式', step2_label: '连接账户', step3_label: '启动 Yinyang',
      progress_step: '第 {step} 步 / 共 3 步', progress_complete: '已完成 {count} / 3',
      step1_title: '选择 Yinyang 的驱动方式。', step1_copy: '可免费使用 BYOK，或自动检测本地 CLI 包装器。两种方式都保持本地优先。',
      step1_primary: '使用 BYOK', step1_secondary: '自动检测本地 CLI',
      step1_notes_1: '如果你已有自己的模型提供商，请使用 BYOK。', step1_notes_2: '如果本机已有 Codex、Claude Code、Gemini 或 Aider，请使用本地 CLI。',
      step2_title: '需要更多能力时再连接 Solace AGI 账户。', step2_copy: '免费或付费账户可解锁云同步、远程控制、团队能力和托管 LLM 增强。',
      step2_primary: '登录 / 创建账户', step2_secondary: '继续本地优先',
      step2_notes_1: '免费账户可让 dashboard、Morning Brief 和云端知道你是谁。', step2_notes_2: '你也可以现在跳过，继续使用本地优先模式。',
      step3_title: '打开 Solace Browser 并在 Yinyang 中完成。', step3_copy: '浏览器打开后，固定的 Yinyang 侧栏会安装应用、创建计划并引导后续操作。',
      step3_primary: '打开 Solace Browser', step3_secondary: '打开智能体指南',
      step3_notes_1: '浏览器会打开真实的 Solace AGI dashboard。', step3_notes_2: '固定的 Yinyang 侧栏是应用、计划与自动化的工作区。'
    },
    pt: {
      toolbar_language: 'Idioma', toolbar_theme: 'Tema', toolbar_text: 'Texto',
      summary: 'O Solace Hub controla a saude local, o acesso de agentes na porta 8888 e o lancamento do navegador.',
      open_browser: 'Abrir Solace Browser', quick_setup: 'Configuracao rapida', quick_setup_title: 'Tres passos para um assistente pronto',
      step1_label: 'Escolher modo local', step2_label: 'Conectar conta', step3_label: 'Abrir Yinyang',
      progress_step: 'Passo {step} de 3', progress_complete: 'Concluido {count} / 3',
      step1_title: 'Escolha como dar energia ao Yinyang.', step1_copy: 'Comece gratis com BYOK ou detecte um CLI local. Os dois caminhos continuam local-first.',
      step1_primary: 'Usar BYOK', step1_secondary: 'Detectar CLI local',
      step1_notes_1: 'Use BYOK se voce ja tiver seu proprio provedor de modelo.', step1_notes_2: 'Use CLI local se Codex, Claude Code, Gemini ou Aider ja existirem nesta maquina.',
      step2_title: 'Conecte sua conta Solace AGI quando quiser mais.', step2_copy: 'Uma conta gratis ou paga libera sincronizacao, controle remoto, equipe e LLM gerenciado.',
      step2_primary: 'Entrar / Criar conta', step2_secondary: 'Continuar local-first',
      step2_notes_1: 'Uma conta gratis permite que dashboard, Morning Brief e nuvem saibam quem voce e.', step2_notes_2: 'Voce pode pular isso e continuar local-first agora.',
      step3_title: 'Abra o Solace Browser e termine dentro do Yinyang.', step3_copy: 'Quando o navegador abrir, a barra lateral fixa do Yinyang pode instalar apps, criar agendas e orientar o restante.',
      step3_primary: 'Abrir Solace Browser', step3_secondary: 'Abrir guia de agentes',
      step3_notes_1: 'O navegador abre no dashboard real do Solace AGI.', step3_notes_2: 'A barra lateral fixa do Yinyang e onde apps, agendas e automacoes vivem.'
    },
    fr: {
      toolbar_language: 'Langue', toolbar_theme: 'Theme', toolbar_text: 'Texte',
      summary: 'Solace Hub gere la sante locale, l acces agent sur le port 8888 et le lancement du navigateur.',
      open_browser: 'Ouvrir Solace Browser', quick_setup: 'Configuration rapide', quick_setup_title: 'Trois etapes pour un assistant pret',
      step1_label: 'Choisir le mode local', step2_label: 'Connecter le compte', step3_label: 'Lancer Yinyang',
      progress_step: 'Etape {step} sur 3', progress_complete: 'Termine {count} / 3',
      step1_title: 'Choisissez comment alimenter Yinyang.', step1_copy: 'Commencez gratuitement avec BYOK ou detectez un CLI local. Les deux chemins restent local-first.',
      step1_primary: 'Utiliser BYOK', step1_secondary: 'Detecter le CLI local',
      step1_notes_1: 'Utilisez BYOK si vous avez deja votre propre fournisseur de modele.', step1_notes_2: 'Utilisez le CLI local si Codex, Claude Code, Gemini ou Aider vivent deja sur cette machine.',
      step2_title: 'Connectez votre compte Solace AGI quand vous voulez plus.', step2_copy: 'Un compte gratuit ou payant debloque la synchronisation cloud, le controle distant, l equipe et les uplifts LLM.',
      step2_primary: 'Se connecter / Creer un compte', step2_secondary: 'Rester local-first',
      step2_notes_1: 'Un compte gratuit permet au dashboard, a Morning Brief et au cloud de savoir qui vous etes.', step2_notes_2: 'Vous pouvez ignorer cela et rester en mode local-first maintenant.',
      step3_title: 'Ouvrez Solace Browser et terminez dans Yinyang.', step3_copy: 'Une fois le navigateur ouvert, la barre laterale epinglee de Yinyang peut installer des apps, creer des horaires et guider la suite.',
      step3_primary: 'Ouvrir Solace Browser', step3_secondary: 'Ouvrir le guide agent',
      step3_notes_1: 'Le navigateur s ouvre sur le vrai dashboard Solace AGI.', step3_notes_2: 'La barre laterale epinglee de Yinyang est l endroit ou vivent apps, horaires et automatisations.'
    },
    de: {
      toolbar_language: 'Sprache', toolbar_theme: 'Thema', toolbar_text: 'Text',
      summary: 'Solace Hub steuert den lokalen Zustand, den Agentenzugriff auf Port 8888 und den Browserstart.',
      open_browser: 'Solace Browser offnen', quick_setup: 'Schnellstart', quick_setup_title: 'Drei Schritte zu einem einsatzbereiten Assistenten',
      step1_label: 'Lokalen Modus wahlen', step2_label: 'Konto verbinden', step3_label: 'Yinyang starten',
      progress_step: 'Schritt {step} von 3', progress_complete: 'Fertig {count} / 3',
      step1_title: 'Wahle, wie Yinyang angetrieben wird.', step1_copy: 'Starte kostenlos mit BYOK oder erkenne einen lokalen CLI Wrapper. Beide Wege bleiben local-first.',
      step1_primary: 'BYOK verwenden', step1_secondary: 'Lokalen CLI erkennen',
      step1_notes_1: 'Nutze BYOK, wenn du bereits deinen eigenen Modellanbieter hast.', step1_notes_2: 'Nutze lokalen CLI, wenn Codex, Claude Code, Gemini oder Aider schon auf diesem Rechner laufen.',
      step2_title: 'Verbinde dein Solace AGI Konto, wenn du mehr willst.', step2_copy: 'Ein kostenloses oder bezahltes Konto schaltet Cloud Sync, Fernsteuerung, Teams und verwaltete LLM Uplifts frei.',
      step2_primary: 'Anmelden / Konto erstellen', step2_secondary: 'Lokal-first bleiben',
      step2_notes_1: 'Ein kostenloses Konto erlaubt dashboard, Morning Brief und Cloud zu wissen, wer du bist.', step2_notes_2: 'Du kannst das uberspringen und jetzt lokal-first bleiben.',
      step3_title: 'Offne Solace Browser und schliesse in Yinyang ab.', step3_copy: 'Sobald der Browser offen ist, kann die angeheftete Yinyang Seitenleiste Apps installieren, Zeitplane erstellen und den Rest fuhren.',
      step3_primary: 'Solace Browser offnen', step3_secondary: 'Agentenleitfaden offnen',
      step3_notes_1: 'Der Browser offnet das echte Solace AGI dashboard.', step3_notes_2: 'Die angeheftete Yinyang Seitenleiste ist der Ort fur Apps, Plane und Automatisierung.'
    },
    ja: {
      toolbar_language: '言語', toolbar_theme: 'テーマ', toolbar_text: '文字',
      summary: 'Solace Hub はローカル実行状態、8888 ポートのエージェントアクセス、そしてブラウザ起動を管理します。',
      open_browser: 'Solace Browser を開く', quick_setup: 'クイック設定', quick_setup_title: '使えるアシスタントまで 3 ステップ',
      step1_label: 'ローカルモードを選ぶ', step2_label: 'アカウント接続', step3_label: 'Yinyang を起動',
      progress_step: 'ステップ {step} / 3', progress_complete: '完了 {count} / 3',
      step1_title: 'Yinyang の動力源を選びます。', step1_copy: '無料で BYOK を使うか、ローカル CLI ラッパーを自動検出できます。どちらも local-first です。',
      step1_primary: 'BYOK を使う', step1_secondary: 'ローカル CLI を検出',
      step1_notes_1: 'すでに自分のモデル提供元があるなら BYOK を使ってください。', step1_notes_2: 'このマシンに Codex、Claude Code、Gemini、Aider があるならローカル CLI を使ってください。',
      step2_title: 'もっと必要になったら Solace AGI アカウントを接続します。', step2_copy: '無料または有料アカウントでクラウド同期、遠隔操作、チーム機能、管理 LLM 強化が使えます。',
      step2_primary: 'サインイン / アカウント作成', step2_secondary: 'ローカルのまま続ける',
      step2_notes_1: '無料アカウントでも dashboard、Morning Brief、cloud があなたを識別できます。', step2_notes_2: '今はスキップして local-first のまま使い続けられます。',
      step3_title: 'Solace Browser を開いて Yinyang の中で続けます。', step3_copy: 'ブラウザが開くと、固定された Yinyang サイドバーがアプリ導入、スケジュール作成、残りの案内を行います。',
      step3_primary: 'Solace Browser を開く', step3_secondary: 'エージェントガイドを開く',
      step3_notes_1: 'ブラウザは本物の Solace AGI dashboard を開きます。', step3_notes_2: '固定された Yinyang サイドバーがアプリ、予定、自動化の中心です。'
    }
  };
  const EXTRA_TRANSLATIONS = {
    en: {
      quick_setup_title: 'Turn on apps in three steps',
      step1_label: 'Sign in',
      step2_label: 'Choose model source',
      step3_label: 'Launch browser',
      step1_title: 'Sign in or create an account.',
      step1_copy: 'Logged out keeps AI Agent access on. Apps stay off until you sign in.',
      step1_primary: 'Sign In / Create Account',
      step1_secondary: 'Stay in agent mode',
      step1_notes_1: 'Free and paid both start by signing in.',
      step1_notes_2: 'Apps stay off until you both sign in and choose a model source.',
      step2_title: 'Choose how free or paid apps run.',
      step2_copy: 'Free users turn apps on with BYOK, Local CLI, or Ollama. Paid users can turn on managed AI.',
      step2_primary: 'Use BYOK',
      step2_secondary: 'Autodetect Local CLI',
      step2_notes_1: 'Use Ollama if you already have a model server on your network.',
      step2_notes_2: 'Managed AI is for paid memberships and uses Solace AGI credits.',
      step3_title: 'Open Browser and finish inside Yinyang.',
      step3_copy: 'Once Browser opens, Yinyang can run apps, save reports, and schedule work.',
      step3_primary: 'Open Solace Browser',
      step3_secondary: 'Open Agent Guide',
      free_kicker: '1. Default: Free',
      free_pill: 'Default',
      free_heading: 'AI Agent Access:',
      free_enabled: 'Enabled',
      free_copy: 'Point your AI coding agent to http://localhost:8888/agents to learn how to control Solace Browser through the local runtime. Give an agent one URL and it can get to work. Local control stays on this machine unless you choose cloud features later.',
      personal_kicker: '2. Personal AI Assistant (Always Free)',
      personal_heading: 'Stay local and start gently',
      personal_copy: 'Use BYOK or autodetect a local coding CLI wrapper to get one useful workflow and one saved report while keeping keys and runs on this machine.',
      personal_benefit_1: 'Bring your own key and keep full local-first control',
      personal_benefit_2: 'Autodetect Codex, Claude Code, Gemini, or Aider wrappers in minutes',
      personal_benefit_3: 'Use Yinyang for free on supported domains and bundled starter apps with saved reports',
      pro_kicker: '3. Managed Solace AGI (Dragon Warrior)',
      pro_heading: 'Extend the same protected workflow to your team and other machines',
      pro_copy: 'Sign in only after the local run is useful and you want managed AI, cloud sync, remote control, eSign, or audit-ready proof on top of it.',
      pro_benefit_1: 'Managed AI so teams do not have to wire BYOK or local wrappers on every machine',
      pro_benefit_2: 'Remote access, tunnel relay, sync, backups, and shared team access when you explicitly decide this workflow should leave the machine',
      pro_benefit_3: 'Enterprise evidence, approvals, schedules, and audit-ready workflows when proof matters most',
      pro_note: 'Start free first. Upgrade only when the local win feels steady enough to carry to more people, more machines, and shared workflows you are willing to expose beyond local-only mode.',
      runtime_kicker: '4. Know if the system is healthy',
      runtime_heading: 'Runtime Status',
      status_mcp_label: 'MCP server',
      status_webservices_label: 'Webservices :8888',
      status_free_label: 'Free version',
      status_yinyang_label: 'Yinyang sidebar',
      status_remote_label: 'Remote access',
      status_sync_label: 'Solace AGI sync',
      runtime_footer_note: 'Advanced admin stays behind the runtime API so the default surface stays smaller and safer.',
      launch_in_progress: 'Launching…',
      opened: 'Opened',
      saving: 'Saving…',
      detecting: 'Detecting…',
      runtime_healthy: 'localhost:8888 is healthy. Agent access and Browser launch are ready.',
      runtime_offline: 'localhost:8888 is offline. Agent access and Browser launch will resume after Hub restarts.',
      runtime_unreachable: 'Cannot reach localhost:8888: {error}',
      runtime_summary_mismatch: 'Hub reports {status}, but localhost:8888 is still catching up.',
      agent_access_configured: 'Agent access is listening on http://localhost:8888/agents. Point Codex, Claude Code, Cursor, or Gemini there when you are ready.',
      agent_access_first_run: 'First launch defaults to AI Agent Access. The Hub will complete setup the first time you open the Browser.',
      account_signed_in: 'Signed in',
      account_not_signed_in: 'Later',
      setup_waiting: 'No local mode saved yet. Choose one, then open Solace Browser.',
      setup_local_cli_saved: 'Local CLI mode saved. Browser can open now.',
      setup_local_mode_saved: 'Local mode saved. Browser can open now.',
      setup_account_connected: 'Account connected. Next, open Solace Browser and finish in Yinyang.',
      setup_browser_active: 'Browser session active. Yinyang is pinned in the Browser.',
      setup_runtime_unavailable: 'Runtime unavailable. Restart Hub first.',
      status_ready_local_agents: 'MCP and agent access ready',
      status_hub_runtime_offline: 'Runtime offline',
      status_listening_8888: 'Port 8888 ready',
      status_server_unavailable: 'Unavailable',
      status_agent_access_available: 'Agents listening on /agents',
      status_connected: 'On',
      status_off: 'Off',
      status_waiting_browser: 'Waiting for Browser',
      cli_wrappers_detected: 'Detected local coding agents: {tools}.',
      cli_wrappers_none: 'No local coding agents detected yet.',
      cli_wrappers_unavailable: 'Local coding agent check unavailable until runtime recovers.',
      byok_saved: 'BYOK saved. Open Solace Browser and use Yinyang to finish provider setup.',
      byok_save_failed: 'Could not save BYOK setup: {error}',
      byok_mode_active: 'BYOK mode is active. Your provider key stays local-first here, and you can add an account later if you want.',
      cli_mode_saved: 'CLI wrapper mode saved. Detected: {tools}.',
      cli_mode_saved_none: 'CLI wrapper mode saved. No supported local CLIs detected yet.',
      cli_mode_failed: 'Could not enable Local CLI Wrapper: {error}',
      cli_mode_active: 'Local CLI Wrapper mode is active. Local wrappers run here, and you can add an account later if you want.',
      browser_launch_failed: 'Could not launch Solace Browser: {error}',
      browser_open_url_failed: 'Could not open requested page in Solace Browser: {error}'
    },
    es: {
      free_kicker: '1. Gratis para siempre', free_heading: 'Acceso para agentes IA:', free_enabled: 'Activado',
      free_pill: 'Gratis para siempre',
      free_copy: 'Indica a cualquier agente de codigo IA que vaya a http://localhost:8888/agents para aprender a controlar Solace Browser mediante el runtime local. Este modo es gratis y local-first.',
      personal_kicker: '2. Asistente personal de IA (siempre gratis)', personal_heading: 'Impulsa Yinyang a tu manera',
      personal_copy: 'Configura BYOK o detecta un CLI local y usa el webservice wrapper de Solace CLI para dar energia a tu asistente Yinyang.',
      personal_benefit_1: 'Trae tu propia clave y manten el control local-first', personal_benefit_2: 'Detecta wrappers de Codex, Claude Code, Gemini o Aider', personal_benefit_3: 'Usa Yinyang gratis en dominios compatibles y apps incluidas',
      pro_kicker: '3. Asistente profesional de IA (Dragon Warrior)', pro_heading: 'Solace AGI de nivel empresarial',
      pro_copy: 'Inicia sesion para obtener IA empresarial con eSign, evidencia FDA Part 11, sincronizacion de equipo, copias de seguridad, control remoto y uplifts de LLM gestionado.',
      pro_benefit_1: 'LLM gestionado con uplifts y recomendaciones premium', pro_benefit_2: 'Acceso remoto, tunel, sincronizacion, copias y coordinacion de equipo', pro_benefit_3: 'Evidencia empresarial, aprobaciones, horarios y flujos listos para auditoria',
      pro_note: 'Mas informacion en solaceagi.com y usa la misma cuenta en Hub, Browser y cloud.',
      runtime_kicker: '4. Comprueba si el sistema esta sano', runtime_heading: 'Estado del runtime',
      status_mcp_label: 'Servidor MCP', status_webservices_label: 'Webservices :8888', status_free_label: 'Version gratis', status_yinyang_label: 'Barra lateral Yinyang', status_remote_label: 'Acceso remoto', status_sync_label: 'Sincronizacion Solace AGI',
      runtime_footer_note: 'La administracion avanzada queda detras del runtime para que el primer inicio siga siendo simple.',
      launch_in_progress: 'Abriendo…', opened: 'Abierto', saving: 'Guardando…', detecting: 'Detectando…',
      runtime_healthy: 'El runtime local esta sano en localhost:8888.', runtime_offline: 'El runtime local esta desconectado. Inicia Solace Hub otra vez para restaurar el runtime gratuito.', runtime_unreachable: 'No se pudo acceder a localhost:8888: {error}', runtime_summary_mismatch: 'Hub informa {status}, pero localhost:8888 todavia no esta sano.',
      agent_access_configured: 'El acceso de agentes esta configurado. Indica a Codex, Claude Code, Cursor o Gemini que usen http://localhost:8888/agents.', agent_access_first_run: 'El primer inicio usa Acceso de Agente IA por defecto. Hub completara la configuracion la primera vez que abras el Browser.',
      account_signed_in: 'Con sesion iniciada', account_not_signed_in: 'Sin iniciar sesion',
      setup_waiting: 'Esperando BYOK, CLI local o modo agente.', setup_local_cli_saved: 'Modo CLI local guardado. La cuenta es opcional.', setup_local_mode_saved: 'Modo local guardado. La cuenta es opcional.', setup_account_connected: 'La cuenta esta conectada. Abre Solace Browser para continuar en Yinyang.', setup_browser_active: 'La sesion del navegador esta activa. Continua en la barra lateral fija de Yinyang.', setup_runtime_unavailable: 'Runtime no disponible. Reinicia Hub primero.',
      status_ready_local_agents: 'Listo para agentes locales', status_hub_runtime_offline: 'Runtime de Hub desconectado', status_listening_8888: 'Escuchando en 8888', status_server_unavailable: 'Servidor no disponible', status_agent_access_available: 'Acceso de agentes disponible', status_connected: 'Conectado', status_off: 'Apagado', status_waiting_browser: 'Esperando navegador',
      cli_wrappers_detected: 'Wrappers CLI detectados: {tools}.', cli_wrappers_none: 'Wrappers CLI: aun no se detectan agentes locales.', cli_wrappers_unavailable: 'Wrappers CLI: runtime no disponible.',
      byok_saved: 'BYOK guardado. Abre Solace Browser y usa Yinyang para terminar la configuracion del proveedor.', byok_save_failed: 'No se pudo guardar BYOK: {error}', byok_mode_active: 'El modo BYOK esta activo. Sigues en modo local-first y sin iniciar sesion en Solace AGI.',
      cli_mode_saved: 'Modo CLI wrapper guardado. Detectados: {tools}.', cli_mode_saved_none: 'Modo CLI wrapper guardado. Todavia no se detectan CLIs compatibles.', cli_mode_failed: 'No se pudo activar Local CLI Wrapper: {error}', cli_mode_active: 'El modo Local CLI Wrapper esta activo. Sigues en modo local-first y sin iniciar sesion en Solace AGI.',
      browser_launch_failed: 'No se pudo abrir Solace Browser: {error}', browser_open_url_failed: 'No se pudo abrir la pagina solicitada en Solace Browser: {error}'
    },
    vi: {
      free_kicker: '1. Mien phi mai mai', free_heading: 'Truy cap tac tu AI:', free_enabled: 'Bat',
      free_pill: 'Mien phi mai mai',
      free_copy: 'Hay chi bat ky tac tu AI den http://localhost:8888/agents de hoc cach dieu khien Solace Browser qua runtime cuc bo. Che do nay mien phi va local-first.',
      personal_kicker: '2. Tro ly AI ca nhan (luon mien phi)', personal_heading: 'Van hanh Yinyang theo cach cua ban',
      personal_copy: 'Thiet lap BYOK hoac tu dong tim CLI local va dung webservice wrapper cua Solace CLI de cap suc manh cho Yinyang.',
      personal_benefit_1: 'Dung khoa cua ban va giu quyen kiem soat local-first', personal_benefit_2: 'Tu dong tim wrapper Codex, Claude Code, Gemini hoac Aider', personal_benefit_3: 'Dung Yinyang mien phi tren domain ho tro va app co san',
      pro_kicker: '3. Tro ly AI chuyen nghiep (Dragon Warrior)', pro_heading: 'Solace AGI cap doanh nghiep',
      pro_copy: 'Dang nhap de nhan AI cap doanh nghiep voi eSign, FDA Part 11, dong bo nhom, sao luu, dieu khien tu xa va uplift LLM quan ly.',
      pro_benefit_1: 'LLM quan ly voi uplift va de xuat cao cap', pro_benefit_2: 'Truy cap tu xa, tunnel, dong bo, sao luu va phoi hop nhom', pro_benefit_3: 'Bang chung doanh nghiep, phe duyet, lich va quy trinh san sang kiem toan',
      pro_note: 'Xem them tai solaceagi.com va dung cung mot tai khoan cho Hub, Browser va cloud.',
      runtime_kicker: '4. Biet he thong co khoe hay khong', runtime_heading: 'Trang thai runtime',
      status_mcp_label: 'May chu MCP', status_webservices_label: 'Webservices :8888', status_free_label: 'Ban mien phi', status_yinyang_label: 'Thanh ben Yinyang', status_remote_label: 'Truy cap tu xa', status_sync_label: 'Dong bo Solace AGI',
      runtime_footer_note: 'Quan tri nang cao nam sau runtime de lan dau mo van don gian.',
      launch_in_progress: 'Dang mo…', opened: 'Da mo', saving: 'Dang luu…', detecting: 'Dang tim…',
      runtime_healthy: 'Runtime cuc bo dang khoe tren localhost:8888.', runtime_offline: 'Runtime cuc bo dang tat. Hay mo lai Solace Hub de khoi phuc runtime mien phi.', runtime_unreachable: 'Khong the ket noi localhost:8888: {error}', runtime_summary_mismatch: 'Hub bao {status}, nhung localhost:8888 van chua khoe.',
      agent_access_configured: 'Truy cap agent da duoc cau hinh. Hay chi Codex, Claude Code, Cursor hoac Gemini den http://localhost:8888/agents.', agent_access_first_run: 'Lan mo dau mac dinh la AI Agent Access. Hub se hoan tat thiet lap lan dau ban mo Browser.',
      account_signed_in: 'Da dang nhap', account_not_signed_in: 'Chua dang nhap',
      setup_waiting: 'Dang cho BYOK, CLI local hoac che do agent.', setup_local_cli_saved: 'Da luu che do CLI local. Tai khoan la tuy chon.', setup_local_mode_saved: 'Da luu che do local. Tai khoan la tuy chon.', setup_account_connected: 'Tai khoan da ket noi. Mo Solace Browser de tiep tuc trong Yinyang.', setup_browser_active: 'Phien browser dang hoat dong. Tiep tuc trong thanh ben Yinyang.', setup_runtime_unavailable: 'Runtime khong kha dung. Hay khoi dong lai Hub truoc.',
      status_ready_local_agents: 'San sang cho agent local', status_hub_runtime_offline: 'Runtime Hub dang tat', status_listening_8888: 'Dang lang nghe o 8888', status_server_unavailable: 'May chu khong kha dung', status_agent_access_available: 'Da co truy cap agent', status_connected: 'Da ket noi', status_off: 'Tat', status_waiting_browser: 'Dang cho Browser',
      cli_wrappers_detected: 'Da phat hien wrapper CLI: {tools}.', cli_wrappers_none: 'CLI wrappers: chua phat hien agent code local.', cli_wrappers_unavailable: 'CLI wrappers: runtime khong kha dung.',
      byok_saved: 'Da luu BYOK. Mo Solace Browser va dung Yinyang de hoan tat cai dat nha cung cap.', byok_save_failed: 'Khong the luu BYOK: {error}', byok_mode_active: 'Che do BYOK dang hoat dong. Ban van local-first va chua dang nhap Solace AGI.',
      cli_mode_saved: 'Da luu che do CLI wrapper. Da tim thay: {tools}.', cli_mode_saved_none: 'Da luu che do CLI wrapper. Chua tim thay CLI duoc ho tro.', cli_mode_failed: 'Khong the bat Local CLI Wrapper: {error}', cli_mode_active: 'Che do Local CLI Wrapper dang hoat dong. Ban van local-first va chua dang nhap Solace AGI.',
      browser_launch_failed: 'Khong the mo Solace Browser: {error}', browser_open_url_failed: 'Khong the mo trang duoc yeu cau trong Solace Browser: {error}'
    },
    zh: {
      free_kicker: '1. 永久免费', free_heading: 'AI 智能体访问：', free_enabled: '已启用',
      free_pill: '永久免费',
      free_copy: '让任何 AI 编码智能体访问 http://localhost:8888/agents，学习如何通过本地运行时控制 Solace Browser。这个模式免费且本地优先。',
      personal_kicker: '2. 个人 AI 助手（永久免费）', personal_heading: '按你的方式驱动 Yinyang',
      personal_copy: '可使用 BYOK，或自动检测本地 CLI，并通过 Solace CLI wrapper webservice 为 Yinyang 提供能力。',
      personal_benefit_1: '使用你自己的密钥并保持本地优先控制', personal_benefit_2: '自动检测 Codex、Claude Code、Gemini 或 Aider wrapper', personal_benefit_3: '在支持的域和内置应用上免费使用 Yinyang',
      pro_kicker: '3. 专业 AI 助手（Dragon Warrior）', pro_heading: '企业级 Solace AGI',
      pro_copy: '登录即可获得企业级 AI，包括 eSign、FDA Part 11 证据、团队同步、备份、远程控制和托管 LLM 增强。',
      pro_benefit_1: '托管 LLM 与高级应用增强和推荐', pro_benefit_2: '远程访问、隧道中继、同步、备份和团队协作', pro_benefit_3: '企业级证据、审批、计划和审计就绪工作流',
      pro_note: '前往 solaceagi.com 了解更多，并在 Hub、Browser 和云端使用同一账号。',
      runtime_kicker: '4. 了解系统是否健康', runtime_heading: '运行时状态',
      status_mcp_label: 'MCP 服务器', status_webservices_label: 'Webservices :8888', status_free_label: '免费版本', status_yinyang_label: 'Yinyang 侧栏', status_remote_label: '远程访问', status_sync_label: 'Solace AGI 同步',
      runtime_footer_note: '高级管理留在运行时之后，以保持首次启动足够简单。',
      launch_in_progress: '正在打开…', opened: '已打开', saving: '正在保存…', detecting: '正在检测…',
      runtime_healthy: '本地运行时在 localhost:8888 上健康运行。', runtime_offline: '本地运行时离线。请重新启动 Solace Hub 以恢复免费智能体运行时。', runtime_unreachable: '无法访问 localhost:8888：{error}', runtime_summary_mismatch: 'Hub 报告为 {status}，但 localhost:8888 仍未健康。',
      agent_access_configured: '智能体访问已配置。请让 Codex、Claude Code、Cursor 或 Gemini 访问 http://localhost:8888/agents。', agent_access_first_run: '首次启动默认启用 AI Agent Access。Hub 会在你第一次打开 Browser 时完成设置。',
      account_signed_in: '已登录', account_not_signed_in: '未登录',
      setup_waiting: '等待 BYOK、本地 CLI 或智能体模式。', setup_local_cli_saved: '本地 CLI 模式已保存。账户连接是可选的。', setup_local_mode_saved: '本地模式已保存。账户连接是可选的。', setup_account_connected: '账户已连接。打开 Solace Browser 以继续进入 Yinyang。', setup_browser_active: '浏览器会话已激活。请继续使用固定的 Yinyang 侧栏。', setup_runtime_unavailable: '运行时不可用。请先重启 Hub。',
      status_ready_local_agents: '本地智能体已就绪', status_hub_runtime_offline: 'Hub 运行时离线', status_listening_8888: '正在监听 8888', status_server_unavailable: '服务器不可用', status_agent_access_available: '智能体访问可用', status_connected: '已连接', status_off: '关闭', status_waiting_browser: '等待浏览器',
      cli_wrappers_detected: '已检测到 CLI wrapper：{tools}。', cli_wrappers_none: 'CLI wrappers：尚未检测到本地编码智能体。', cli_wrappers_unavailable: 'CLI wrappers：运行时不可用。',
      byok_saved: 'BYOK 已保存。打开 Solace Browser 并使用 Yinyang 完成提供商设置。', byok_save_failed: '无法保存 BYOK：{error}', byok_mode_active: 'BYOK 模式已激活。你仍然保持本地优先，且尚未登录 Solace AGI。', cli_mode_saved: 'CLI wrapper 模式已保存。已检测到：{tools}。', cli_mode_saved_none: 'CLI wrapper 模式已保存。尚未检测到受支持的本地 CLI。', cli_mode_failed: '无法启用 Local CLI Wrapper：{error}', cli_mode_active: 'Local CLI Wrapper 模式已激活。你仍然保持本地优先，且尚未登录 Solace AGI。',
      browser_launch_failed: '无法打开 Solace Browser：{error}', browser_open_url_failed: '无法在 Solace Browser 中打开请求的页面：{error}'
    },
    pt: {
      free_kicker: '1. Gratis para sempre', free_heading: 'Acesso de agente de IA:', free_enabled: 'Ativado',
      free_pill: 'Gratis para sempre',
      free_copy: 'Aponte qualquer agente de codigo com IA para http://localhost:8888/agents para aprender a controlar o Solace Browser pelo runtime local. Esse modo e gratuito e local-first.',
      personal_kicker: '2. Assistente pessoal de IA (sempre gratis)', personal_heading: 'Ative o Yinyang do seu jeito',
      personal_copy: 'Configure BYOK ou detecte um CLI local e use o webservice wrapper do Solace CLI para alimentar seu assistente Yinyang.',
      personal_benefit_1: 'Traga sua propria chave e mantenha o controle local-first', personal_benefit_2: 'Detecte wrappers do Codex, Claude Code, Gemini ou Aider', personal_benefit_3: 'Use o Yinyang gratis em dominios suportados e apps iniciais',
      pro_kicker: '3. Assistente profissional de IA (Dragon Warrior)', pro_heading: 'Solace AGI de nivel empresarial',
      pro_copy: 'Entre para ter IA empresarial com eSign, evidencias FDA Part 11, sincronizacao em equipe, backups, controle remoto e uplifts de LLM gerenciado.',
      pro_benefit_1: 'LLM gerenciado com uplifts e recomendacoes premium', pro_benefit_2: 'Acesso remoto, tunel, sincronizacao, backups e coordenacao de equipe', pro_benefit_3: 'Evidencias empresariais, aprovacoes, agendas e fluxos prontos para auditoria',
      pro_note: 'Saiba mais em solaceagi.com e use a mesma conta no Hub, Browser e cloud.',
      runtime_kicker: '4. Saiba se o sistema esta saudavel', runtime_heading: 'Status do runtime',
      status_mcp_label: 'Servidor MCP', status_webservices_label: 'Webservices :8888', status_free_label: 'Versao gratuita', status_yinyang_label: 'Barra lateral Yinyang', status_remote_label: 'Acesso remoto', status_sync_label: 'Sincronizacao Solace AGI',
      runtime_footer_note: 'A administracao avancada fica atras do runtime para manter o primeiro uso simples.',
      launch_in_progress: 'Abrindo…', opened: 'Aberto', saving: 'Salvando…', detecting: 'Detectando…',
      runtime_healthy: 'O runtime local esta saudavel em localhost:8888.', runtime_offline: 'O runtime local esta offline. Inicie o Solace Hub novamente para restaurar o runtime gratuito.', runtime_unreachable: 'Nao foi possivel acessar localhost:8888: {error}', runtime_summary_mismatch: 'O Hub informa {status}, mas localhost:8888 ainda nao esta saudavel.',
      agent_access_configured: 'O acesso de agentes esta configurado. Aponte Codex, Claude Code, Cursor ou Gemini para http://localhost:8888/agents.', agent_access_first_run: 'O primeiro uso vem com AI Agent Access por padrao. O Hub concluira a configuracao quando voce abrir o Browser pela primeira vez.',
      account_signed_in: 'Conectado', account_not_signed_in: 'Nao conectado',
      setup_waiting: 'Aguardando BYOK, CLI local ou modo agente.', setup_local_cli_saved: 'Modo CLI local salvo. A conexao de conta e opcional.', setup_local_mode_saved: 'Modo local salvo. A conexao de conta e opcional.', setup_account_connected: 'A conta esta conectada. Abra o Solace Browser para continuar no Yinyang.', setup_browser_active: 'A sessao do navegador esta ativa. Continue na barra lateral fixa do Yinyang.', setup_runtime_unavailable: 'Runtime indisponivel. Reinicie o Hub primeiro.',
      status_ready_local_agents: 'Pronto para agentes locais', status_hub_runtime_offline: 'Runtime do Hub offline', status_listening_8888: 'Escutando em 8888', status_server_unavailable: 'Servidor indisponivel', status_agent_access_available: 'Acesso de agentes disponivel', status_connected: 'Conectado', status_off: 'Desligado', status_waiting_browser: 'Aguardando navegador',
      cli_wrappers_detected: 'Wrappers CLI detectados: {tools}.', cli_wrappers_none: 'CLI wrappers: nenhum agente local detectado ainda.', cli_wrappers_unavailable: 'CLI wrappers: runtime indisponivel.',
      byok_saved: 'BYOK salvo. Abra o Solace Browser e use o Yinyang para terminar a configuracao do provedor.', byok_save_failed: 'Nao foi possivel salvar o BYOK: {error}', byok_mode_active: 'O modo BYOK esta ativo. Voce continua local-first e nao esta conectado ao Solace AGI.', cli_mode_saved: 'Modo CLI wrapper salvo. Detectados: {tools}.', cli_mode_saved_none: 'Modo CLI wrapper salvo. Nenhum CLI suportado foi detectado ainda.', cli_mode_failed: 'Nao foi possivel ativar o Local CLI Wrapper: {error}', cli_mode_active: 'O modo Local CLI Wrapper esta ativo. Voce continua local-first e nao esta conectado ao Solace AGI.',
      browser_launch_failed: 'Nao foi possivel abrir o Solace Browser: {error}', browser_open_url_failed: 'Nao foi possivel abrir a pagina solicitada no Solace Browser: {error}'
    }
  };
  const SETUP_STEPS = {
    1: {
      titleKey: 'step1_title',
      copyKey: 'step1_copy',
      primaryKey: 'step1_primary',
      secondaryKey: 'step1_secondary',
      noteKeys: ['step1_notes_1', 'step1_notes_2']
    },
    2: {
      titleKey: 'step2_title',
      copyKey: 'step2_copy',
      primaryKey: 'step2_primary',
      secondaryKey: 'step2_secondary',
      noteKeys: ['step2_notes_1', 'step2_notes_2']
    },
    3: {
      titleKey: 'step3_title',
      copyKey: 'step3_copy',
      primaryKey: 'step3_primary',
      secondaryKey: 'step3_secondary',
      noteKeys: ['step3_notes_1', 'step3_notes_2']
    }
  };

  function qs(id) {
    return document.getElementById(id);
  }

  function hubUrl(path) {
    return HUB_API_BASE + path;
  }

  async function hubFetch(path, options) {
    return fetch(hubUrl(path), options);
  }

  function timeoutSignal(ms) {
    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
      return AbortSignal.timeout(ms);
    }
    const controller = new AbortController();
    window.setTimeout(function () {
      controller.abort();
    }, ms);
    return controller.signal;
  }

  async function invoke(cmd, args) {
    if (!tauri) {
      throw new Error('Tauri bridge unavailable');
    }
    if (typeof tauri.invoke === 'function') {
      return tauri.invoke(cmd, args || {});
    }
    if (tauri.tauri && typeof tauri.tauri.invoke === 'function') {
      return tauri.tauri.invoke(cmd, args || {});
    }
    throw new Error('Tauri invoke unavailable');
  }

  function setText(id, value) {
    const element = qs(id);
    if (element) {
      element.textContent = value;
    }
  }

  function setButtonActive(id, active) {
    const button = qs(id);
    if (!button) {
      return;
    }
    if (active) {
      button.classList.add('hub-toolbar-button-active');
    } else {
      button.classList.remove('hub-toolbar-button-active');
    }
  }

  function currentLocale() {
    return document.documentElement.lang || 'en';
  }

  function translationTable(locale) {
    return Object.assign(
      {},
      TRANSLATIONS.en,
      EXTRA_TRANSLATIONS.en,
      TRANSLATIONS[locale] || {},
      EXTRA_TRANSLATIONS[locale] || {}
    );
  }

  function t(key, params, locale) {
    const table = translationTable(locale || currentLocale());
    let value = table[key] || TRANSLATIONS.en[key] || key;
    if (!params) {
      return value;
    }
    Object.keys(params).forEach(function (paramKey) {
      value = value.replace('{' + paramKey + '}', String(params[paramKey]));
    });
    return value;
  }

  function stepContent(stepNumber) {
    const step = SETUP_STEPS[stepNumber];
    return {
      title: t(step.titleKey),
      copy: t(step.copyKey),
      primaryLabel: t(step.primaryKey),
      secondaryLabel: t(step.secondaryKey),
      notes: step.noteKeys.map(function (noteKey) {
        return t(noteKey);
      })
    };
  }

  function applyTranslations() {
    setText('hub-label-language', t('toolbar_language'));
    setText('hub-label-theme', t('toolbar_theme'));
    setText('hub-label-text', t('toolbar_text'));
    setText('hub-summary-text', t('summary'));
    setText('btn-open-browser', t('open_browser'));
    setText('setup-kicker', t('quick_setup'));
    setText('setup-heading', t('quick_setup_title'));
    setText('setup-step-1-label', t('step1_label'));
    setText('setup-step-2-label', t('step2_label'));
    setText('setup-step-3-label', t('step3_label'));
    setText('free-kicker', t('free_kicker'));
    setText('free-heading-text', t('free_heading'));
    setText('agent-toggle-label', t('free_enabled'));
    setText('free-copy', t('free_copy'));
    setText('personal-kicker', t('personal_kicker'));
    setText('personal-heading', t('personal_heading'));
    setText('personal-pill', t('free_pill'));
    setText('personal-copy', t('personal_copy'));
    setText('personal-benefit-1', t('personal_benefit_1'));
    setText('personal-benefit-2', t('personal_benefit_2'));
    setText('personal-benefit-3', t('personal_benefit_3'));
    setText('pro-kicker', t('pro_kicker'));
    setText('pro-heading', t('pro_heading'));
    setText('pro-copy', t('pro_copy'));
    setText('pro-benefit-1', t('pro_benefit_1'));
    setText('pro-benefit-2', t('pro_benefit_2'));
    setText('pro-benefit-3', t('pro_benefit_3'));
    setText('pro-note', t('pro_note'));
    setText('runtime-kicker', t('runtime_kicker'));
    setText('runtime-heading', t('runtime_heading'));
    setText('status-mcp-label', t('status_mcp_label'));
    setText('status-webservices-label', t('status_webservices_label'));
    setText('status-free-label', t('status_free_label'));
    setText('status-yinyang-label', t('status_yinyang_label'));
    setText('status-remote-label', t('status_remote_label'));
    setText('status-sync-label', t('status_sync_label'));
    setText('runtime-footer-note', t('runtime_footer_note'));

    const primary = qs('setup-step-primary');
    if (primary && !primary.disabled) {
      const activeStep = Number(primary.getAttribute('data-step') || '1');
      setSetupStep(activeStep);
    }
  }

  function setSetupStep(stepNumber, statusText) {
    const content = stepContent(stepNumber);
    Object.keys(SETUP_STEPS).forEach(function (key) {
      const isActive = String(stepNumber) === key;
      const button = qs('setup-step-' + key);
      if (!button) {
        return;
      }
      button.classList.toggle('hub-setup-step-active', isActive);
      button.setAttribute('aria-selected', isActive ? 'true' : 'false');
      button.setAttribute('tabindex', isActive ? '0' : '-1');
    });
    const panel = qs('hub-setup-panel');
    if (panel) {
      panel.setAttribute('aria-labelledby', 'setup-step-' + stepNumber);
    }
    setText('setup-step-title', content.title);
    setText('setup-step-copy', content.copy);
    if (statusText) {
      setText('setup-step-status', statusText);
    }
    setText('setup-progress-pill', t('progress_step', { step: stepNumber }));
    const notes = qs('setup-step-notes');
    if (notes) {
      notes.innerHTML = '';
      content.notes.forEach(function (note) {
        const item = document.createElement('li');
        item.textContent = note;
        notes.appendChild(item);
      });
    }
    const primary = qs('setup-step-primary');
    const secondary = qs('setup-step-secondary');
    if (primary) {
      primary.textContent = content.primaryLabel;
      primary.setAttribute('data-step', String(stepNumber));
    }
    if (secondary) {
      secondary.textContent = content.secondaryLabel;
      secondary.setAttribute('data-step', String(stepNumber));
    }
  }

  function setSetupComplete(stepNumber, complete) {
    const button = qs('setup-step-' + stepNumber);
    if (!button) {
      return;
    }
    button.classList.toggle('hub-setup-step-complete', complete);
  }

  function highestCompletedStep(loggedIn, appsOn, browserActive) {
    if (browserActive) {
      return 3;
    }
    if (appsOn) {
      return 2;
    }
    if (loggedIn) {
      return 1;
    }
    return 0;
  }

  function localeDisplayName(locale) {
    try {
      const displayNames = new Intl.DisplayNames([locale], { type: 'language' });
      return displayNames.of(locale);
    } catch (error) {
      return locale;
    }
  }

  function setLocale(locale) {
    const nextLocale = HUB_LOCALES.indexOf(locale) >= 0 ? locale : 'en';
    document.documentElement.lang = nextLocale;
    document.documentElement.dir = RTL_LOCALES.indexOf(nextLocale) >= 0 ? 'rtl' : 'ltr';
    window.localStorage.setItem(HUB_LOCALE_KEY, nextLocale);
    setText('language-current', localeDisplayName(nextLocale));
    applyTranslations();
    const menu = qs('hub-language-menu');
    if (!menu) {
      return;
    }
    Array.from(menu.querySelectorAll('[data-locale]')).forEach(function (button) {
      button.setAttribute('aria-current', button.getAttribute('data-locale') === nextLocale ? 'true' : 'false');
    });
  }

  function bindLanguageMenu() {
    const button = qs('btn-language-menu');
    const menu = qs('hub-language-menu');
    if (!button || !menu) {
      return;
    }

    menu.innerHTML = '';
    HUB_LOCALES.forEach(function (locale) {
      const option = document.createElement('button');
      option.type = 'button';
      option.className = 'hub-language-option';
      option.setAttribute('role', 'menuitemradio');
      option.setAttribute('data-locale', locale);
      option.textContent = localeDisplayName(locale);
      option.addEventListener('click', function () {
        setLocale(locale);
        menu.hidden = true;
        button.setAttribute('aria-expanded', 'false');
      });
      menu.appendChild(option);
    });

    button.addEventListener('click', function () {
      const expanded = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      menu.hidden = expanded;
    });

    document.addEventListener('click', function (event) {
      if (!menu.hidden && !menu.contains(event.target) && event.target !== button && !button.contains(event.target)) {
        menu.hidden = true;
        button.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function bindSetupRail() {
    [1, 2, 3].forEach(function (stepNumber) {
      const button = qs('setup-step-' + stepNumber);
      if (!button) {
        return;
      }
      button.addEventListener('click', function () {
        setSetupStep(stepNumber);
      });
      button.addEventListener('keydown', function (event) {
        if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') {
          return;
        }
        const tabs = [1, 2, 3]
          .map(function (step) { return qs('setup-step-' + step); })
          .filter(Boolean);
        const currentIndex = tabs.indexOf(button);
        if (currentIndex === -1 || !tabs.length) {
          return;
        }
        event.preventDefault();
        const direction = event.key === 'ArrowRight' ? 1 : -1;
        const nextIndex = (currentIndex + direction + tabs.length) % tabs.length;
        const nextButton = tabs[nextIndex];
        if (!nextButton) {
          return;
        }
        nextButton.focus();
        setSetupStep(Number(nextButton.getAttribute('data-step') || nextIndex + 1));
      });
    });

    const primary = qs('setup-step-primary');
    const secondary = qs('setup-step-secondary');
    if (primary) {
      primary.addEventListener('click', async function () {
        const step = primary.getAttribute('data-step') || '1';
        if (step === '1') {
          qs('btn-open-account').click();
          return;
        }
        if (step === '2') {
          qs('btn-enable-byok').click();
          return;
        }
        if (step === '3') {
          qs('btn-open-browser').click();
        }
      });
    }
    if (secondary) {
      secondary.addEventListener('click', async function () {
        const step = secondary.getAttribute('data-step') || '1';
        if (step === '1') {
          setText('agent-note', 'Agent-only mode stays on. Sign in later to turn on apps.');
          return;
        }
        if (step === '2') {
          qs('btn-enable-cli').click();
          return;
        }
        if (step === '3') {
          openBrowserUrl('http://127.0.0.1:8888/agents', 'setup-step-secondary');
        }
      });
    }
  }

  function applyAppearance(theme, fontScale) {
    const root = document.documentElement;
    const nextTheme = theme || 'auto';
    const nextFontScale = fontScale || 'medium';
    root.setAttribute('data-theme', nextTheme);
    root.setAttribute('data-font-scale', nextFontScale);
    window.localStorage.setItem(HUB_THEME_KEY, nextTheme);
    window.localStorage.setItem(HUB_FONT_KEY, nextFontScale);

    setButtonActive('btn-theme-auto', nextTheme === 'auto');
    setButtonActive('btn-theme-light', nextTheme === 'light');
    setButtonActive('btn-theme-dark', nextTheme === 'dark');
  }

  function bindAppearanceControls() {
    const themeAuto = qs('btn-theme-auto');
    const themeLight = qs('btn-theme-light');
    const themeDark = qs('btn-theme-dark');
    const fontDown = qs('btn-font-down');
    const fontUp = qs('btn-font-up');
    const fontOrder = ['small', 'medium', 'large'];

    themeAuto.addEventListener('click', function () {
      applyAppearance('auto', document.documentElement.getAttribute('data-font-scale'));
    });
    themeLight.addEventListener('click', function () {
      applyAppearance('light', document.documentElement.getAttribute('data-font-scale'));
    });
    themeDark.addEventListener('click', function () {
      applyAppearance('dark', document.documentElement.getAttribute('data-font-scale'));
    });

    fontDown.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-font-scale') || 'medium';
      const currentIndex = Math.max(fontOrder.indexOf(current), 0);
      const nextScale = fontOrder[Math.max(currentIndex - 1, 0)];
      applyAppearance(document.documentElement.getAttribute('data-theme') || 'auto', nextScale);
    });

    fontUp.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-font-scale') || 'medium';
      const currentIndex = Math.max(fontOrder.indexOf(current), 0);
      const nextScale = fontOrder[Math.min(currentIndex + 1, fontOrder.length - 1)];
      applyAppearance(document.documentElement.getAttribute('data-theme') || 'auto', nextScale);
    });
  }

  function setStatusCard(id, ok, text) {
    const card = qs(id);
    if (!card) {
      return;
    }
    card.className = ok ? 'hub-status-card hub-status-card-on' : 'hub-status-card hub-status-card-off';
    const copy = qs(id + '-copy');
    if (copy) {
      copy.textContent = text;
    }
  }

  function setButtonBusy(button, busyKey) {
    if (!button) {
      return '';
    }
    const original = button.textContent;
    button.disabled = true;
    button.textContent = t(busyKey);
    return original;
  }

  function normalizeMembershipTier(value) {
    const tier = String(value || '').trim().toLowerCase();
    if (['free', 'starter', 'pro', 'team', 'enterprise'].indexOf(tier) >= 0) {
      return tier;
    }
    if (tier === 'paid') {
      return 'starter';
    }
    return 'free';
  }

  function normalizeOnboardingState(payload) {
    const source = payload || {};
    const authState = source.auth_state === 'logged_in' ? 'logged_in' : 'logged_out';
    const membershipTier = normalizeMembershipTier(source.membership_tier);
    const modelSource = ['byok', 'cli', 'ollama', 'managed'].indexOf(source.model_source) >= 0
      ? source.model_source
      : null;
    const managedLlmEnabled = Boolean(source.managed_llm_enabled) || modelSource === 'managed' || membershipTier !== 'free';
    const appsEnabled = Boolean(source.apps_enabled) || (
      authState === 'logged_in' && (
        managedLlmEnabled ||
        modelSource === 'byok' ||
        modelSource === 'cli' ||
        modelSource === 'ollama'
      )
    );

    return {
      completed: Boolean(source.completed),
      mode: source.mode || null,
      auth_state: authState,
      membership_tier: membershipTier,
      model_source: modelSource,
      managed_llm_enabled: managedLlmEnabled,
      apps_enabled: appsEnabled,
      device_id: source.device_id || null
    };
  }

  function isLoggedIn(onboarding) {
    return normalizeOnboardingState(onboarding).auth_state === 'logged_in';
  }

  function appsEnabled(onboarding) {
    return normalizeOnboardingState(onboarding).apps_enabled;
  }

  async function fetchOnboardingState() {
    const statusResponse = await hubFetch('/api/v1/onboarding/status', {
      signal: timeoutSignal(3000)
    });
    if (!statusResponse.ok) {
      return normalizeOnboardingState({});
    }
    return normalizeOnboardingState(await statusResponse.json());
  }

  async function saveOnboarding(payload) {
    const completeResponse = await hubFetch('/onboarding/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: timeoutSignal(5000)
    });
    if (!completeResponse.ok) {
      throw new Error('HTTP ' + completeResponse.status);
    }
    return normalizeOnboardingState(await completeResponse.json());
  }

  async function configureOllamaFromPrompt() {
    const current = await hubFetch('/api/v1/ollama/config', { signal: timeoutSignal(3000) });
    let defaultUrl = 'http://192.168.1.1:11434';
    if (current.ok) {
      const payload = await current.json();
      if (payload && payload.url) {
        defaultUrl = payload.url;
      }
    }
    const url = window.prompt('Enter your Ollama server URL', defaultUrl);
    if (!url) {
      return null;
    }
    const trimmed = url.trim();
    if (!trimmed) {
      return null;
    }
    const response = await hubFetch('/api/v1/ollama/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: trimmed }),
      signal: timeoutSignal(8000)
    });
    if (!response.ok) {
      let detail = 'HTTP ' + response.status;
      try {
        const payload = await response.json();
        detail = payload.error || payload.detail || detail;
      } catch (error) {
        // keep HTTP detail
      }
      throw new Error(detail);
    }
    return response.json();
  }

  async function openBrowser() {
    const button = qs('btn-open-browser');
    const original = setButtonBusy(button, 'launch_in_progress');
    try {
      const response = await hubFetch('/api/v1/hub/browser/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://solaceagi.com/dashboard', profile: 'default', mode: 'standard' }),
        signal: timeoutSignal(15000)
      });
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      button.textContent = t('opened');
      await refreshHub();
    } catch (error) {
      setText('agent-note', t('browser_launch_failed', { error: error.message }));
      button.textContent = original;
      button.disabled = false;
      return;
    }
    window.setTimeout(function () {
      button.textContent = original;
      button.disabled = false;
    }, 2500);
  }

  async function openBrowserUrl(url, buttonId) {
    const button = qs(buttonId);
    const original = setButtonBusy(button, 'launch_in_progress');
    try {
      const response = await hubFetch('/api/v1/hub/browser/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, profile: 'default', mode: 'standard' }),
        signal: timeoutSignal(15000)
      });
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      button.textContent = t('opened');
      await refreshHub();
    } catch (error) {
      setText('agent-note', t('browser_open_url_failed', { error: error.message }));
      button.textContent = original;
      button.disabled = false;
      return;
    }
    window.setTimeout(function () {
      button.textContent = original;
      button.disabled = false;
    }, 2500);
  }

  function bindActions() {
    qs('btn-open-browser').addEventListener('click', openBrowser);
    qs('btn-open-account').addEventListener('click', function () {
      openBrowserUrl('https://solaceagi.com/register', 'btn-open-account');
    });
    qs('btn-enable-byok').addEventListener('click', async function () {
      const button = this;
      const original = setButtonBusy(button, 'saving');
      try {
        await saveOnboarding({
          auth_state: 'logged_in',
          membership_tier: 'free',
          managed_llm_enabled: false,
          model_source: 'byok'
        });
        setText('personal-note', t('byok_saved'));
        await refreshHub();
      } catch (error) {
        setText('personal-note', t('byok_save_failed', { error: error.message }));
      } finally {
        button.textContent = original;
        button.disabled = false;
      }
    });
    qs('btn-enable-cli').addEventListener('click', async function () {
      const button = this;
      const original = setButtonBusy(button, 'detecting');
      try {
        const cli = await hubFetch('/api/v1/cli/detect', { signal: timeoutSignal(5000) });
        if (!cli.ok) {
          throw new Error('HTTP ' + cli.status);
        }
        const payload = await cli.json();
        const detected = Object.keys(payload.detected || {}).filter(function (tool) {
          return payload.detected[tool] && payload.detected[tool].installed;
        });
        await saveOnboarding({
          auth_state: 'logged_in',
          membership_tier: 'free',
          managed_llm_enabled: false,
          model_source: 'cli'
        });
        setText(
          'personal-note',
          detected.length
            ? t('cli_mode_saved', { tools: detected.join(', ') })
            : t('cli_mode_saved_none')
        );
        await refreshHub();
      } catch (error) {
        setText('personal-note', t('cli_mode_failed', { error: error.message }));
      } finally {
        button.textContent = original;
        button.disabled = false;
      }
    });
    qs('btn-enable-ollama').addEventListener('click', async function () {
      const button = this;
      const original = setButtonBusy(button, 'saving');
      try {
        const payload = await configureOllamaFromPrompt();
        if (!payload) {
          setText('personal-note', 'Ollama setup cancelled. Apps stay off until you choose a model source.');
        } else {
          await saveOnboarding({
            auth_state: 'logged_in',
            membership_tier: 'free',
            managed_llm_enabled: false,
            model_source: 'ollama'
          });
          setText('personal-note', 'Ollama URL saved. Apps are ready on your remote Ollama server.');
        }
        await refreshHub();
      } catch (error) {
        setText('personal-note', 'Could not save Ollama URL: ' + error.message);
      } finally {
        button.textContent = original;
        button.disabled = false;
      }
    });
    qs('agent-access-toggle').addEventListener('change', function () {
      this.checked = true;
    });
  }

  async function refreshHub() {
    try {
      const [statusResponse, onboardingResponse, summaryResponse, tunnelResponse, syncResponse, sessionsResponse, cliResponse] = await Promise.all([
        hubFetch('/api/status', { signal: timeoutSignal(3000) }),
        hubFetch('/api/v1/onboarding/status', { signal: timeoutSignal(3000) }),
        hubFetch('/api/v1/hub/summary', { signal: timeoutSignal(3000) }),
        hubFetch('/api/v1/tunnel/status', { signal: timeoutSignal(3000) }),
        hubFetch('/api/v1/sync/status', { signal: timeoutSignal(3000) }),
        hubFetch('/api/v1/sessions', { signal: timeoutSignal(3000) }),
        hubFetch('/api/v1/cli/detect', { signal: timeoutSignal(3000) })
      ]);

      const status = statusResponse.ok ? await statusResponse.json() : { status: 'offline' };
      const onboarding = onboardingResponse.ok ? normalizeOnboardingState(await onboardingResponse.json()) : normalizeOnboardingState({});
      const summary = summaryResponse.ok ? await summaryResponse.json() : {};
      const tunnel = tunnelResponse.ok ? await tunnelResponse.json() : { active: false };
      const sync = syncResponse.ok ? await syncResponse.json() : { status: 'offline' };
      const sessions = sessionsResponse.ok ? await sessionsResponse.json() : { sessions: [] };
      const cli = cliResponse.ok ? await cliResponse.json() : { detected: {} };

      const runtimeHealthy = status.status === 'ok';
      const browserActive = Array.isArray(sessions.sessions) && sessions.sessions.length > 0;
      const syncHealthy = runtimeHealthy && sync.status && sync.status !== 'offline' && sync.status !== 'idle';
      const tunnelHealthy = runtimeHealthy && Boolean(tunnel.active);
      const loggedIn = isLoggedIn(onboarding);
      const membershipTier = onboarding.membership_tier || 'free';
      const modelSource = onboarding.model_source || null;
      const managedLlmEnabled = Boolean(onboarding.managed_llm_enabled);
      const localSetupComplete = appsEnabled(onboarding);
      const completedStep = highestCompletedStep(loggedIn, localSetupComplete, browserActive);

      setText(
        'runtime-summary',
        runtimeHealthy
          ? t('runtime_healthy')
          : t('runtime_offline')
      );
      setText('agent-access-label', runtimeHealthy ? 'ON' : 'WAITING');
      setText(
        'agent-note',
        loggedIn
          ? 'Signed in. Pick BYOK, Local CLI, Ollama, or managed AI to turn apps on.'
          : 'Logged out. AI Agent Access stays on, but apps stay off until you sign in.'
      );
      setText('account-pill', loggedIn ? (membershipTier === 'free' ? 'Free member' : 'Paid member') : 'Logged out');
      qs('account-pill').className = loggedIn ? 'hub-pill hub-pill-on' : 'hub-pill hub-pill-off';
      setSetupComplete(1, loggedIn);
      setSetupComplete(2, localSetupComplete);
      setSetupComplete(3, browserActive);
      if (!loggedIn) {
        setSetupStep(1, t('setup_waiting'));
      } else if (!localSetupComplete) {
        setSetupStep(2, modelSource === 'managed'
          ? 'Managed AI is selected. Open the Browser to finish inside Yinyang.'
          : 'Pick one model source to turn apps on.');
      } else if (!browserActive) {
        setSetupStep(3, managedLlmEnabled
          ? 'Managed AI is active. Open Solace Browser to finish inside Yinyang.'
          : 'Apps are on. Open Solace Browser to finish inside Yinyang.');
      } else {
        setSetupStep(3, t('setup_browser_active'));
      }
      const progress = qs('setup-progress-pill');
      if (progress) {
        progress.textContent = completedStep > 0
          ? t('progress_complete', { count: completedStep })
          : t('progress_step', { step: 1 });
      }

      setStatusCard('status-mcp', runtimeHealthy, runtimeHealthy ? t('status_ready_local_agents') : t('status_hub_runtime_offline'));
      setStatusCard('status-webservices', runtimeHealthy, runtimeHealthy ? t('status_listening_8888') : t('status_server_unavailable'));
      setStatusCard('status-free', true, t('status_agent_access_available'));
      setStatusCard('status-yinyang', browserActive, browserActive ? t('setup_browser_active') : t('status_waiting_browser'));
      setStatusCard('status-remote', tunnelHealthy, tunnelHealthy ? t('status_connected') : t('status_off'));
      setStatusCard('status-sync', syncHealthy, syncHealthy ? sync.status : t('status_off'));

      const detectedTools = Object.keys(cli.detected || {}).filter(function (tool) {
        return cli.detected[tool] && cli.detected[tool].installed;
      });
      setText(
        'cli-note',
        detectedTools.length
          ? t('cli_wrappers_detected', { tools: detectedTools.join(', ') })
          : t('cli_wrappers_none')
      );
      if (!loggedIn) {
        setText('personal-note', 'Sign in first. Apps stay off while AI Agent Access remains available at /agents.');
      } else if (modelSource === 'byok') {
        setText('personal-note', t('byok_mode_active'));
      } else if (modelSource === 'cli') {
        setText('personal-note', t('cli_mode_active'));
      } else if (modelSource === 'ollama') {
        setText('personal-note', 'Ollama mode is active. Apps use your saved remote Ollama server.');
      } else if (modelSource === 'managed') {
        setText('personal-note', 'Managed AI is active. Open the dashboard for cloud controls and credits.');
      } else {
        setText('personal-note', 'Sign in is complete. Pick BYOK, Local CLI, Ollama, or managed AI to turn apps on.');
      }
      if (summary.status && !runtimeHealthy) {
        setText('runtime-summary', t('runtime_summary_mismatch', { status: summary.status }));
      }
    } catch (error) {
      setText('runtime-summary', t('runtime_unreachable', { error: error.message }));
      setStatusCard('status-mcp', false, t('status_off'));
      setStatusCard('status-webservices', false, t('status_off'));
      setStatusCard('status-yinyang', false, t('status_waiting_browser'));
      setStatusCard('status-remote', false, t('status_off'));
      setStatusCard('status-sync', false, t('status_off'));
      setText('cli-note', t('cli_wrappers_unavailable'));
      setText('agent-access-label', 'WAITING');
      setText('agent-note', t('runtime_offline'));
      setText('account-pill', 'Logged out');
      qs('account-pill').className = 'hub-pill hub-pill-off';
      setSetupComplete(1, false);
      setSetupComplete(2, false);
      setSetupComplete(3, false);
      setSetupStep(1, t('setup_runtime_unavailable'));
    }
  }

  async function boot() {
    window.scrollTo(0, 0);
    bindSetupRail();
    bindLanguageMenu();
    setLocale(window.localStorage.getItem(HUB_LOCALE_KEY) || 'en');
    applyAppearance(
      window.localStorage.getItem(HUB_THEME_KEY) || 'auto',
      window.localStorage.getItem(HUB_FONT_KEY) || 'medium'
    );
    bindAppearanceControls();
    bindActions();
    await refreshHub();
  }

  document.addEventListener('DOMContentLoaded', boot);
}());
