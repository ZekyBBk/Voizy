using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using System.Security.Principal;

namespace VoizyBuilder
{
    public class BuilderForm : Form
    {
        // Paleta Deep Dark pura estilo BBk2FA con acentos Neon Lime
        private static readonly Color WindowBg = Color.FromArgb(10, 12, 16);
        private static readonly Color CardBg = Color.FromArgb(18, 20, 26);
        private static readonly Color BorderColor = Color.FromArgb(30, 35, 48);
        private static readonly Color AccentEmerald = Color.FromArgb(170, 201, 12);     // #AAC90C
        private static readonly Color AccentEmeraldHover = Color.FromArgb(189, 224, 14); // #BDE00E
        private static readonly Color AccentRed = Color.FromArgb(239, 68, 68);          // #EF4444
        private static readonly Color TextPrimary = Color.FromArgb(241, 245, 249);
        private static readonly Color TextSecondary = Color.FromArgb(156, 163, 175);
        private static readonly Color ConsoleBg = Color.FromArgb(6, 7, 9);
        private static readonly Color ButtonDarkBg = Color.FromArgb(22, 26, 35);
        private static readonly Color TitleBarBg = Color.FromArgb(10, 12, 16);

        // Win32 APIs para esquinas redondeadas y arrastre de ventana
        [DllImport("user32.dll")]
        public static extern bool ReleaseCapture();
        [DllImport("user32.dll")]
        public static extern int SendMessage(IntPtr hWnd, int Msg, int wParam, int lParam);
        [DllImport("gdi32.dll")]
        public static extern IntPtr CreateRoundRectRgn(int nLeftRect, int nTopRect, int nRightRect, int nBottomRect, int nWidthEllipse, int nHeightEllipse);
        [DllImport("dwmapi.dll")]
        public static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

        private const int WM_NCLBUTTONDOWN = 0xA1;
        private const int HTCAPTION = 0x2;
        private const int DWMWA_WINDOW_CORNER_PREFERENCE = 33;
        private const int DWMWCP_ROUND = 2;

        private Panel titleBarPanel;
        private Label lblWinTitle;
        private Label lblBadge;
        private Button btnMin;
        private Button btnClose;

        private Panel cardPanel;
        private Label lblTitle;
        private Label lblSubtitle;

        // Controles de Versionado
        private Label lblVerPrompt;
        private TextBox txtVersion;
        private RoundedButton btnPatch;
        private RoundedButton btnMinor;
        private RoundedButton btnMajor;

        private Label lblStatus;
        private Label lblTimer;
        private Stopwatch buildStopwatch = new Stopwatch();
        private Timer uiTimer;
        private CustomProgressBar progressBar;
        private RoundedButton btnBuild;
        private RoundedButton btnOpenFolder;
        private RoundedButton btnCopyLog;
        private RoundedButton btnToggleLogs;
        private Panel logContainer;
        private CustomLogTextBox txtLog;
        private DarkScrollBar logScrollBar;

        private string projectRoot;
        private string outputPath;
        private string logFilePath;
        private bool isBuilding = false;
        private bool isCancellationRequested = false;
        private Process currentRunningProcess = null;
        private bool logsVisible = false;

        private int currentMajor = 1;
        private int currentMinor = 0;
        private int currentPatch = 0;

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.Style |= 0x00020000; // WS_MINIMIZEBOX (permite alternar minimizar desde barra de tareas)
                cp.Style |= 0x00080000; // WS_SYSMENU
                return cp;
            }
        }

        [STAThread]
        public static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // Auto-elevación a Administrador si fuera necesario
            WindowsIdentity identity = WindowsIdentity.GetCurrent();
            WindowsPrincipal principal = new WindowsPrincipal(identity);
            bool isElevated = principal.IsInRole(WindowsBuiltInRole.Administrator);

            if (!isElevated)
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = Application.ExecutablePath,
                        Arguments = string.Join(" ", args),
                        Verb = "runas",
                        UseShellExecute = true
                    };
                    Process.Start(psi);
                    return;
                }
                catch
                {
                    CustomDarkModal.Show(
                        null,
                        "Permisos de Administrador",
                        "Builder.exe requiere permisos de Administrador para instalar y compilar automáticamente en modo silencioso.",
                        isError: true
                    );
                    return;
                }
            }

            Application.Run(new BuilderForm());
        }

        public BuilderForm()
        {
            this.SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);

            string currentDir = AppDomain.CurrentDomain.BaseDirectory;
            DirectoryInfo parent = Directory.GetParent(currentDir);

            if (Directory.Exists(Path.Combine(currentDir, "core")) || File.Exists(Path.Combine(currentDir, "tools", "Voizy.spec")))
            {
                projectRoot = currentDir;
            }
            else if (parent != null && (Directory.Exists(Path.Combine(parent.FullName, "core")) || File.Exists(Path.Combine(parent.FullName, "tools", "Voizy.spec"))))
            {
                projectRoot = parent.FullName;
            }
            else
            {
                projectRoot = @"C:\Voizy";
            }

            outputPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "Voizy.exe");
            string logsDir = Path.Combine(projectRoot, "logs");
            if (!Directory.Exists(logsDir))
            {
                try { Directory.CreateDirectory(logsDir); } catch { }
            }
            logFilePath = Path.Combine(logsDir, "build.log");

            ReadCurrentVersionFromConfig();
            InitializeComponent();
            ApplyRoundedRegion();
        }

        private void ReadCurrentVersionFromConfig()
        {
            try
            {
                string themePath = Path.Combine(projectRoot, "ui", "theme.py");
                if (File.Exists(themePath))
                {
                    string content = File.ReadAllText(themePath);
                    Match m = Regex.Match(content, @"VERSION_APP\s*=\s*""([0-9]+)\.([0-9]+)\.([0-9]+)""");
                    if (m.Success)
                    {
                        currentMajor = int.Parse(m.Groups[1].Value);
                        currentMinor = int.Parse(m.Groups[2].Value);
                        currentPatch = int.Parse(m.Groups[3].Value);
                    }
                }
            }
            catch { }
        }

        private void ApplyRoundedRegion()
        {
            try
            {
                int cornerPreference = DWMWCP_ROUND;
                DwmSetWindowAttribute(this.Handle, DWMWA_WINDOW_CORNER_PREFERENCE, ref cornerPreference, sizeof(int));
            }
            catch { }

            IntPtr rgn = CreateRoundRectRgn(0, 0, this.Width + 1, this.Height + 1, 14, 14);
            this.Region = Region.FromHrgn(rgn);
        }

        protected override void OnResize(EventArgs e)
        {
            base.OnResize(e);
            ApplyRoundedRegion();
        }

        private void InitializeComponent()
        {
            this.Text = "Voizy - Compiler Studio";
            this.FormBorderStyle = FormBorderStyle.None;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = WindowBg;
            this.ForeColor = TextPrimary;
            this.Font = new Font("Segoe UI", 9.5f, FontStyle.Regular);
            this.Size = new Size(620, 345);
            this.MinimumSize = new Size(620, 300);

            string iconPath = Path.Combine(projectRoot, "ui", "assets", "voizy.ico");
            if (!File.Exists(iconPath)) iconPath = Path.Combine(projectRoot, "voizy.ico");
            if (File.Exists(iconPath))
            {
                try { this.Icon = new Icon(iconPath); } catch { }
            }

            // 1. Barra de Título Frameless
            titleBarPanel = new Panel
            {
                Location = new Point(0, 0),
                Size = new Size(620, 38),
                BackColor = TitleBarBg,
                Dock = DockStyle.Top
            };
            titleBarPanel.MouseDown += (s, e) =>
            {
                if (e.Button == MouseButtons.Left)
                {
                    ReleaseCapture();
                    SendMessage(this.Handle, WM_NCLBUTTONDOWN, HTCAPTION, 0);
                }
            };

            PictureBox picIcon = new PictureBox
            {
                Location = new Point(14, 10),
                Size = new Size(18, 18),
                SizeMode = PictureBoxSizeMode.Zoom
            };
            string pngIconPath = Path.Combine(projectRoot, "ui", "assets", "voizy_logo.png");
            if (!File.Exists(pngIconPath)) pngIconPath = Path.Combine(projectRoot, "voizy_logo.png");
            if (File.Exists(pngIconPath))
            {
                try { picIcon.Image = Image.FromFile(pngIconPath); } catch { }
            }
            titleBarPanel.Controls.Add(picIcon);

            lblWinTitle = new Label
            {
                Text = "VOIZY",
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                ForeColor = AccentEmerald,
                Location = new Point(38, 9),
                AutoSize = true
            };
            lblWinTitle.MouseDown += (s, e) =>
            {
                if (e.Button == MouseButtons.Left)
                {
                    ReleaseCapture();
                    SendMessage(this.Handle, WM_NCLBUTTONDOWN, HTCAPTION, 0);
                }
            };
            titleBarPanel.Controls.Add(lblWinTitle);

            lblBadge = new Label
            {
                Text = string.Format("v{0}.{1}.{2}", currentMajor, currentMinor, currentPatch),
                Font = new Font("Segoe UI", 8f, FontStyle.Regular),
                ForeColor = TextSecondary,
                BackColor = Color.FromArgb(24, 27, 36),
                Padding = new Padding(4, 1, 4, 1),
                Location = new Point(94, 9),
                AutoSize = true
            };
            titleBarPanel.Controls.Add(lblBadge);

            btnMin = new Button
            {
                Text = "—",
                Font = new Font("Segoe UI", 8.5f, FontStyle.Regular),
                ForeColor = TextSecondary,
                BackColor = TitleBarBg,
                FlatStyle = FlatStyle.Flat,
                Size = new Size(42, 38),
                Location = new Point(536, 0),
                Cursor = Cursors.Hand
            };
            btnMin.FlatAppearance.BorderSize = 0;
            btnMin.Click += (s, e) => this.WindowState = FormWindowState.Minimized;
            btnMin.MouseEnter += (s, e) => btnMin.BackColor = Color.FromArgb(24, 28, 38);
            btnMin.MouseLeave += (s, e) => btnMin.BackColor = TitleBarBg;
            titleBarPanel.Controls.Add(btnMin);

            btnClose = new Button
            {
                Text = "✕",
                Font = new Font("Segoe UI", 9f, FontStyle.Regular),
                ForeColor = TextSecondary,
                BackColor = TitleBarBg,
                FlatStyle = FlatStyle.Flat,
                Size = new Size(42, 38),
                Location = new Point(578, 0),
                Cursor = Cursors.Hand
            };
            btnClose.FlatAppearance.BorderSize = 0;
            btnClose.Click += (s, e) =>
            {
                if (isBuilding)
                {
                    DialogResult dr = MessageBox.Show(
                        "Hay una compilación en curso. ¿Deseas cancelar y salir?",
                        "Cancelar",
                        MessageBoxButtons.YesNo,
                        MessageBoxIcon.Question
                    );
                    if (dr == DialogResult.Yes)
                    {
                        isCancellationRequested = true;
                        KillRunningProcess();
                        this.Close();
                    }
                }
                else
                {
                    this.Close();
                }
            };
            btnClose.MouseEnter += (s, e) => { btnClose.BackColor = Color.FromArgb(239, 68, 68); btnClose.ForeColor = Color.White; };
            btnClose.MouseLeave += (s, e) => { btnClose.BackColor = TitleBarBg; btnClose.ForeColor = TextSecondary; };
            titleBarPanel.Controls.Add(btnClose);

            this.Controls.Add(titleBarPanel);

            // 2. Contenedor Principal (Card con bordes limpios)
            cardPanel = new Panel
            {
                Location = new Point(18, 48),
                Size = new Size(584, 278),
                BackColor = CardBg
            };
            cardPanel.Paint += CardPanel_Paint;

            lblTitle = new Label
            {
                Text = "Voizy  Compiler Studio",
                Font = new Font("Segoe UI", 15f, FontStyle.Bold),
                ForeColor = TextPrimary,
                Location = new Point(22, 14),
                AutoSize = true
            };

            lblSubtitle = new Label
            {
                Text = "Generador del ejecutable monolítico portable x64 de producción",
                Font = new Font("Segoe UI", 9f, FontStyle.Regular),
                ForeColor = TextSecondary,
                Location = new Point(24, 42),
                AutoSize = true
            };

            // Fila de Gestión de Versión
            lblVerPrompt = new Label
            {
                Text = "Versión:",
                Font = new Font("Segoe UI", 9f, FontStyle.Bold),
                ForeColor = TextSecondary,
                Location = new Point(24, 73),
                AutoSize = true
            };

            txtVersion = new TextBox
            {
                Text = string.Format("{0}.{1}.{2}", currentMajor, currentMinor, currentPatch),
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                ForeColor = AccentEmerald,
                BackColor = Color.FromArgb(12, 14, 19),
                BorderStyle = BorderStyle.FixedSingle,
                TextAlign = HorizontalAlignment.Center,
                Location = new Point(88, 70),
                Size = new Size(90, 24)
            };
            txtVersion.TextChanged += (s, e) =>
            {
                lblBadge.Text = "v" + txtVersion.Text.Trim();
            };

            btnPatch = new RoundedButton
            {
                Text = "+ Patch",
                Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
                ForeColor = TextPrimary,
                BackColor = Color.FromArgb(28, 33, 44),
                Location = new Point(190, 69),
                Size = new Size(72, 26),
                Cursor = Cursors.Hand
            };
            btnPatch.Click += (s, e) => IncrementVersion(0, 0, 1);

            btnMinor = new RoundedButton
            {
                Text = "+ Minor",
                Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
                ForeColor = TextPrimary,
                BackColor = Color.FromArgb(28, 33, 44),
                Location = new Point(268, 69),
                Size = new Size(72, 26),
                Cursor = Cursors.Hand
            };
            btnMinor.Click += (s, e) => IncrementVersion(0, 1, 0);

            btnMajor = new RoundedButton
            {
                Text = "+ Major",
                Font = new Font("Segoe UI", 8.5f, FontStyle.Bold),
                ForeColor = TextPrimary,
                BackColor = Color.FromArgb(28, 33, 44),
                Location = new Point(346, 69),
                Size = new Size(72, 26),
                Cursor = Cursors.Hand
            };
            btnMajor.Click += (s, e) => IncrementVersion(1, 0, 0);

            // Estado y Progreso
            lblStatus = new Label
            {
                Text = "Listo para iniciar compilación.",
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                ForeColor = AccentEmerald,
                Location = new Point(24, 110),
                Size = new Size(420, 20),
                AutoEllipsis = true
            };

            lblTimer = new Label
            {
                Text = "00:00",
                Font = new Font("Consolas", 9.5f, FontStyle.Bold),
                ForeColor = TextSecondary,
                Location = new Point(446, 110),
                Size = new Size(114, 20),
                TextAlign = ContentAlignment.MiddleRight,
                Visible = false
            };

            uiTimer = new Timer { Interval = 500 };
            uiTimer.Tick += (s, e) =>
            {
                if (buildStopwatch.IsRunning)
                {
                    TimeSpan t = buildStopwatch.Elapsed;
                    lblTimer.Text = string.Format("{0:D2}:{1:D2}", (int)t.TotalMinutes, t.Seconds);
                }
            };

            progressBar = new CustomProgressBar
            {
                Location = new Point(24, 134),
                Size = new Size(536, 8),
                Value = 0
            };

            // Botón Principal de Compilación / Cancelación
            btnBuild = new RoundedButton
            {
                Text = "Compilar Voizy.exe",
                Location = new Point(24, 156),
                Size = new Size(190, 40),
                BackColor = AccentEmerald,
                ForeColor = Color.Black,
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            btnBuild.Click += async (s, e) =>
            {
                if (isBuilding)
                {
                    isCancellationRequested = true;
                    KillRunningProcess();
                    UpdateStatus("Cancelando compilación...", progressBar.Value, AccentRed);
                }
                else
                {
                    await StartBuildAsync();
                }
            };

            btnOpenFolder = new RoundedButton
            {
                Text = "Abrir Carpeta",
                Location = new Point(222, 156),
                Size = new Size(115, 40),
                BackColor = ButtonDarkBg,
                ForeColor = TextSecondary,
                Font = new Font("Segoe UI", 9f, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Visible = false
            };
            btnOpenFolder.Click += (s, e) =>
            {
                try
                {
                    if (File.Exists(outputPath))
                    {
                        Process.Start("explorer.exe", "/select,\"" + outputPath + "\"");
                    }
                    else
                    {
                        Process.Start("explorer.exe", Environment.GetFolderPath(Environment.SpecialFolder.Desktop));
                    }
                }
                catch { }
            };

            // Botón Copiar Log
            btnCopyLog = new RoundedButton
            {
                Text = "Copiar Log",
                Location = new Point(345, 156),
                Size = new Size(105, 40),
                BackColor = ButtonDarkBg,
                ForeColor = TextSecondary,
                Font = new Font("Segoe UI", 9f, FontStyle.Regular),
                Cursor = Cursors.Hand
            };
            btnCopyLog.Click += async (s, e) =>
            {
                string textToCopy = txtLog.Text;
                if (string.IsNullOrEmpty(textToCopy) && File.Exists(logFilePath))
                {
                    try { textToCopy = File.ReadAllText(logFilePath); } catch { }
                }
                if (!string.IsNullOrEmpty(textToCopy))
                {
                    try
                    {
                        Clipboard.SetText(textToCopy);
                        string origText = btnCopyLog.Text;
                        btnCopyLog.Text = "Copiado";
                        btnCopyLog.ForeColor = AccentEmerald;
                        await Task.Delay(2000);
                        btnCopyLog.Text = origText;
                        btnCopyLog.ForeColor = TextSecondary;
                    }
                    catch { }
                }
            };

            btnToggleLogs = new RoundedButton
            {
                Text = "Consola",
                Location = new Point(458, 156),
                Size = new Size(102, 40),
                BackColor = ButtonDarkBg,
                ForeColor = TextSecondary,
                Font = new Font("Segoe UI", 9f, FontStyle.Regular),
                Cursor = Cursors.Hand
            };
            btnToggleLogs.Click += (s, e) => ToggleLogs();

            // Consola de Registro
            logContainer = new Panel
            {
                Location = new Point(24, 206),
                Size = new Size(536, 264),
                BackColor = ConsoleBg,
                Visible = false
            };
            logContainer.Paint += LogContainer_Paint;

            txtLog = new CustomLogTextBox
            {
                Location = new Point(10, 10),
                Size = new Size(510, 244),
                BackColor = ConsoleBg,
                ForeColor = Color.FromArgb(200, 210, 220),
                BorderStyle = BorderStyle.None,
                Font = new Font("Consolas", 8.5f),
                Multiline = true,
                ReadOnly = true,
                ScrollBars = RichTextBoxScrollBars.None,
                WordWrap = true
            };
            txtLog.MouseEnter += (s, e) => { if (!txtLog.Focused) txtLog.Focus(); };

            logScrollBar = new DarkScrollBar
            {
                Location = new Point(524, 10),
                Size = new Size(6, 244)
            };
            logScrollBar.BindTextBox(txtLog);

            logContainer.Controls.Add(txtLog);
            logContainer.Controls.Add(logScrollBar);

            cardPanel.Controls.Add(lblTitle);
            cardPanel.Controls.Add(lblSubtitle);
            cardPanel.Controls.Add(lblVerPrompt);
            cardPanel.Controls.Add(txtVersion);
            cardPanel.Controls.Add(btnPatch);
            cardPanel.Controls.Add(btnMinor);
            cardPanel.Controls.Add(btnMajor);
            cardPanel.Controls.Add(lblStatus);
            cardPanel.Controls.Add(lblTimer);
            cardPanel.Controls.Add(progressBar);
            cardPanel.Controls.Add(btnBuild);
            cardPanel.Controls.Add(btnOpenFolder);
            cardPanel.Controls.Add(btnCopyLog);
            cardPanel.Controls.Add(btnToggleLogs);
            cardPanel.Controls.Add(logContainer);

            this.Controls.Add(cardPanel);
        }

        private void CardPanel_Paint(object sender, PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (GraphicsPath path = GetRoundPath(new RectangleF(0, 0, cardPanel.Width - 1, cardPanel.Height - 1), 10))
            {
                using (Pen pen = new Pen(BorderColor, 1))
                {
                    e.Graphics.DrawPath(pen, path);
                }
            }
        }

        private void LogContainer_Paint(object sender, PaintEventArgs e)
        {
            using (Pen pen = new Pen(BorderColor, 1))
            {
                e.Graphics.DrawRectangle(pen, 0, 0, logContainer.Width - 1, logContainer.Height - 1);
            }
        }

        private static GraphicsPath GetRoundPath(RectangleF rect, float radius)
        {
            GraphicsPath path = new GraphicsPath();
            float r = radius;
            path.AddArc(rect.X, rect.Y, r, r, 180, 90);
            path.AddArc(rect.Right - r, rect.Y, r, r, 270, 90);
            path.AddArc(rect.Right - r, rect.Bottom - r, r, r, 0, 90);
            path.AddArc(rect.X, rect.Bottom - r, r, r, 90, 90);
            path.CloseFigure();
            return path;
        }

        private void IncrementVersion(int dMajor, int dMinor, int dPatch)
        {
            ParseVersionFields();
            if (dMajor > 0)
            {
                currentMajor += dMajor;
                currentMinor = 0;
                currentPatch = 0;
            }
            else if (dMinor > 0)
            {
                currentMinor += dMinor;
                currentPatch = 0;
            }
            else if (dPatch > 0)
            {
                currentPatch += dPatch;
            }
            txtVersion.Text = string.Format("{0}.{1}.{2}", currentMajor, currentMinor, currentPatch);
        }

        private void ParseVersionFields()
        {
            try
            {
                string raw = txtVersion.Text.Trim();
                Match m = Regex.Match(raw, @"^([0-9]+)\.([0-9]+)\.([0-9]+)$");
                if (m.Success)
                {
                    currentMajor = int.Parse(m.Groups[1].Value);
                    currentMinor = int.Parse(m.Groups[2].Value);
                    currentPatch = int.Parse(m.Groups[3].Value);
                }
            }
            catch { }
        }

        private void ToggleLogs()
        {
            logsVisible = !logsVisible;
            if (logsVisible)
            {
                this.Height = 560;
                cardPanel.Height = 490;
                logContainer.Visible = true;
                btnToggleLogs.Text = "Consola ▴";
            }
            else
            {
                this.Height = 345;
                cardPanel.Height = 278;
                logContainer.Visible = false;
                btnToggleLogs.Text = "Consola ▾";
            }
            ApplyRoundedRegion();
            cardPanel.Invalidate();
        }

        private void UpdateStatus(string message, int progressPercent, Color? color = null)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new Action(() => UpdateStatus(message, progressPercent, color)));
                return;
            }
            lblStatus.Text = message;
            lblStatus.ForeColor = color.HasValue ? color.Value : TextSecondary;
            progressBar.Value = Math.Max(0, Math.Min(100, progressPercent));
            AppendLog(string.Format("[{0:HH:mm:ss}] {1}", DateTime.Now, message));
        }

        private static readonly Regex AnsiRegex = new Regex(@"\x1B\[[^@-~]*[@-~]", RegexOptions.Compiled);
        private static readonly Regex SizeProgressRegex = new Regex(@"([0-9.]+)\s*(MB|KB|GB)\s*/\s*([0-9.]+)\s*(MB|KB|GB)", RegexOptions.IgnoreCase | RegexOptions.Compiled);
        private int spinnerCount = 0;
        private string lastProgressText = "";

        private void AppendLog(string line)
        {
            if (this.InvokeRequired)
            {
                this.BeginInvoke(new Action(() => AppendLog(line)));
                return;
            }

            if (line == null) return;
            line = AnsiRegex.Replace(line, "").TrimEnd();
            string trimmed = line.Trim();

            if (string.IsNullOrEmpty(trimmed)) return;

            // Ignorar avisos superfluos
            if (trimmed.StartsWith("[notice]") || trimmed.StartsWith("DEPRECATION:")) return;

            // Si es una línea de progreso de tamaño (ej. winget: 12.5 MB / 25.7 MB)
            Match m = SizeProgressRegex.Match(trimmed);
            if (m.Success)
            {
                string cur = m.Groups[1].Value + " " + m.Groups[2].Value.ToUpper();
                string total = m.Groups[3].Value + " " + m.Groups[4].Value.ToUpper();
                string progressMsg = string.Format("[Descarga] {0} de {1}", cur, total);
                
                if (progressMsg != lastProgressText)
                {
                    lastProgressText = progressMsg;
                    lblStatus.Text = string.Format("[1/5] Descargando componentes: {0}", progressMsg);
                    txtLog.AppendText(progressMsg + Environment.NewLine);
                    txtLog.SelectionStart = txtLog.Text.Length;
                    txtLog.ScrollToCaret();
                }
                return;
            }

            // Si es un spinner de terminal (/ \ | -)
            if (trimmed == "/" || trimmed == "\\" || trimmed == "|" || trimmed == "-" || trimmed == "\\\\")
            {
                spinnerCount++;
                if (spinnerCount % 15 == 0)
                {
                    txtLog.AppendText("[*] Instalando componentes en segundo plano... por favor espera." + Environment.NewLine);
                    txtLog.SelectionStart = txtLog.Text.Length;
                    txtLog.ScrollToCaret();
                }
                return;
            }

            // Si la línea contiene caracteres de barra de progreso rotos (â–ˆ)
            if (trimmed.StartsWith("â–") || trimmed.Contains("â–ˆ") || trimmed.Contains("██"))
            {
                return;
            }

            spinnerCount = 0;

            txtLog.AppendText(line + Environment.NewLine);
            txtLog.SelectionStart = txtLog.Text.Length;
            txtLog.ScrollToCaret();
            if (logScrollBar != null) logScrollBar.SyncWithTextBox();

            try
            {
                File.AppendAllText(logFilePath, line + Environment.NewLine, Encoding.UTF8);
            }
            catch { }
        }

        private void SynchronizeProjectVersions(string newVersion)
        {
            try
            {
                string themePath = Path.Combine(projectRoot, "ui", "theme.py");
                if (File.Exists(themePath))
                {
                    string content = File.ReadAllText(themePath);
                    content = Regex.Replace(content, @"VERSION_APP\s*=\s*""[^""]+""", string.Format("VERSION_APP = \"{0}\"", newVersion));
                    File.WriteAllText(themePath, content);
                }
            }
            catch (Exception ex)
            {
                AppendLog(string.Format("[WARN] No se pudo sincronizar versión: {0}", ex.Message));
            }
        }

        private void KillRunningProcess()
        {
            try
            {
                if (currentRunningProcess != null && !currentRunningProcess.HasExited)
                {
                    currentRunningProcess.Kill();
                }
            }
            catch { }
        }

        private async Task EnsureBuildEnvironmentAsync()
        {
            UpdateStatus("[1/5] Verificando entorno de compilación...", 10);
            string gitExe = @"C:\Users\zeky\AppData\Local\Programs\Git\cmd\git.exe";
            if (!File.Exists(gitExe) && !await CheckCommandExistsAsync("git --version"))
            {
                AppendLog("\n[*] Instalando Git de forma silenciosa...");
                await RunCmdScriptAsync("winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity", projectRoot);
            }

            string pythonExe = GetPython312Exe();
            if (!File.Exists(pythonExe) && !await CheckCommandExistsAsync("python --version"))
            {
                AppendLog("\n[*] Instalando Python 3.12 silencioso...");
                await RunCmdScriptAsync("winget install --id Python.Python.3.12 -e --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity", projectRoot);
            }
        }

        private string GetPython312Exe()
        {
            string envPy = Path.Combine(projectRoot, "env", "Scripts", "python.exe");
            if (File.Exists(envPy)) return envPy;

            string[] search = new string[]
            {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Programs\Python\Python312\python.exe"),
                @"C:\Program Files\Python312\python.exe"
            };
            foreach (string p in search)
            {
                if (File.Exists(p)) return p;
            }
            return "python.exe";
        }

        private async Task<bool> CheckCommandExistsAsync(string commandLine)
        {
            try
            {
                int code = await RunCmdScriptAsync(commandLine, projectRoot);
                return code == 0;
            }
            catch { return false; }
        }

        private async Task StartBuildAsync()
        {
            if (isBuilding) return;
            isBuilding = true;
            isCancellationRequested = false;

            btnBuild.Text = "■  Cancelar Compilación";
            btnBuild.BackColor = AccentRed;
            btnBuild.HoverColor = Color.FromArgb(220, 38, 38);
            btnBuild.ForeColor = Color.White;
            btnBuild.HoverTextColor = Color.White;
            btnBuild.BorderColor = Color.Transparent;
            btnBuild.HoverBorderColor = Color.Transparent;
            btnBuild.Enabled = true;

            btnPatch.Enabled = false;
            btnMinor.Enabled = false;
            btnMajor.Enabled = false;
            txtVersion.Enabled = false;
            btnOpenFolder.Visible = false;
            txtLog.Clear();

            try { if (File.Exists(logFilePath)) File.Delete(logFilePath); } catch { }

            if (!logsVisible) ToggleLogs();

            string versionToBuild = txtVersion.Text.Trim();
            if (string.IsNullOrEmpty(versionToBuild)) versionToBuild = "1.0.0";

            buildStopwatch.Restart();
            lblTimer.Text = "⏱ 00:00";
            lblTimer.ForeColor = AccentEmerald;
            lblTimer.Visible = true;
            uiTimer.Start();

            try
            {
                AppendLog("=======================================================================");
                AppendLog(string.Format("    VOIZY - COMPILACIÓN STANDALONE ULTRA LIGERA v{0}", versionToBuild));
                AppendLog("=======================================================================\n");

                SynchronizeProjectVersions(versionToBuild);

                // Paso 1: Entorno Base
                await EnsureBuildEnvironmentAsync();
                if (isCancellationRequested) return;

                // Paso 2: Entorno Virtual & Dependencias Ligeras
                UpdateStatus("[2/5] Preparando motor CTranslate2 y librerías de IA...", 25);
                string envPy = Path.Combine(projectRoot, "env", "Scripts", "python.exe");
                if (!File.Exists(envPy))
                {
                    string basePy = GetPython312Exe();
                    AppendLog("\n[*] Creando entorno virtual en env...");
                    await RunCmdScriptAsync(string.Format("\"{0}\" -m venv env", basePy), projectRoot);
                }

                AppendLog("\n[*] Verificando paquetes base ligeros...");
                await RunCmdScriptAsync(string.Format("\"{0}\" -m pip install --upgrade --no-warn-script-location --disable-pip-version-check --progress-bar off ctranslate2 faster-whisper customtkinter tkinterdnd2 deep-translator pyinstaller requests huggingface_hub Pillow", envPy), projectRoot);
                if (isCancellationRequested) return;

                // Paso 3: PyInstaller (Ejecución directa sin cmd.exe para evitar problemas de comillas)
                UpdateStatus("[3/4] Compilando motor Voizy con PyInstaller...", 60);
                string pyinstallerExe = Path.Combine(projectRoot, "env", "Scripts", "pyinstaller.exe");
                
                string distDir = Path.Combine(projectRoot, "dist");
                string buildDir = Path.Combine(projectRoot, "build");
                if (Directory.Exists(distDir)) try { Directory.Delete(distDir, true); } catch { }
                if (Directory.Exists(buildDir)) try { Directory.Delete(buildDir, true); } catch { }

                string specFile = Path.Combine(projectRoot, "tools", "Voizy.spec");
                if (!File.Exists(specFile)) specFile = Path.Combine(projectRoot, "Voizy.spec");

                AppendLog(string.Format("\n[*] Ejecutando PyInstaller con: {0}", specFile));
                int pyinstCode = await RunProcessDirectAsync(pyinstallerExe, string.Format("--noconfirm \"{0}\"", specFile), projectRoot);
                if (pyinstCode != 0) throw new Exception("Error al compilar con PyInstaller. Código: " + pyinstCode);

                if (isCancellationRequested) return;

                // Paso 4: Empaquetar Payload en ZIP y compilar Voizy.exe Monolítico Standalone con csc.exe
                UpdateStatus("[4/4] Ensamblando Voizy.exe ultra-ligero en Escritorio...", 88);
                AppendLog("\n[*] Empaquetando payload ligero optimizado en ZIP...");

                string distVoizy = Path.Combine(distDir, "Voizy");
                string payloadZip = Path.Combine(projectRoot, "payload.zip");
                if (File.Exists(payloadZip)) File.Delete(payloadZip);

                await Task.Run(() => ZipFile.CreateFromDirectory(distVoizy, payloadZip, CompressionLevel.Optimal, false));

                string csc = @"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe";
                if (!File.Exists(csc)) csc = @"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe";

                string launcherSrc = Path.Combine(projectRoot, "tools", "launcher.cs");
                string iconFile = Path.Combine(projectRoot, "ui", "assets", "voizy.ico");
                if (!File.Exists(iconFile)) iconFile = Path.Combine(projectRoot, "voizy.ico");

                string logoFile = Path.Combine(projectRoot, "ui", "assets", "voizy_logo.png");

                string cscArgs = string.Format(
                    "/nologo /optimize+ /target:winexe /win32icon:\"{0}\" /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.IO.Compression.dll /r:System.IO.Compression.FileSystem.dll /resource:\"{0}\" /resource:\"{1}\" /resource:\"{2}\" /out:\"{3}\" \"{4}\"",
                    iconFile, payloadZip, logoFile, outputPath, launcherSrc
                );

                AppendLog("\n[*] Ensamblando binario monolítico con csc.exe...");
                int cscCode = await RunProcessDirectAsync(csc, cscArgs, projectRoot);

                // Limpieza de payload.zip temporal
                try { if (File.Exists(payloadZip)) File.Delete(payloadZip); } catch { }

                if (cscCode != 0) throw new Exception("Error al compilar el ejecutable monolítico con csc.exe. Código: " + cscCode);

                long finalSizeMB = new FileInfo(outputPath).Length / (1024 * 1024);

                // Éxito
                uiTimer.Stop();
                buildStopwatch.Stop();
                TimeSpan totalTime = buildStopwatch.Elapsed;
                lblTimer.Text = string.Format("⏱ {0:D2}:{1:D2}", (int)totalTime.TotalMinutes, totalTime.Seconds);
                UpdateStatus(string.Format("✓ ¡Compilación completada con éxito! ({0} MB)", finalSizeMB), 100, AccentEmerald);

                AppendLog("\n=======================================================================");
                AppendLog(" [OK] Voizy.exe ultra ligero listo en tu Escritorio:");
                AppendLog(string.Format(" {0} ({1} MB)", outputPath, finalSizeMB));
                AppendLog(string.Format(" Tiempo total: {0}m {1}s", (int)totalTime.TotalMinutes, totalTime.Seconds));
                AppendLog("=======================================================================\n");

                btnOpenFolder.Visible = true;
            }
            catch (Exception ex)
            {
                uiTimer.Stop();
                buildStopwatch.Stop();
                UpdateStatus("✕ Fallo en la compilación: " + ex.Message, 0, AccentRed);
                AppendLog("\n[ERROR] " + ex.Message);
            }
            finally
            {
                isBuilding = false;
                btnBuild.Text = "▶  Compilar Voizy.exe";
                btnBuild.BackColor = AccentEmerald;
                btnBuild.HoverColor = AccentEmeraldHover;
                btnBuild.ForeColor = Color.Black;
                btnBuild.HoverTextColor = Color.Black;
                btnBuild.BorderColor = Color.FromArgb(30, 35, 48);
                btnBuild.HoverBorderColor = AccentEmerald;
                btnBuild.Enabled = true;

                btnPatch.Enabled = true;
                btnMinor.Enabled = true;
                btnMajor.Enabled = true;
                txtVersion.Enabled = true;
            }
        }

        private async Task<int> RunCmdScriptAsync(string command, string workingDir)
        {
            return await Task.Run(() =>
            {
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = "/c " + command,
                    WorkingDirectory = workingDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8,
                    CreateNoWindow = true
                };

                using (Process proc = new Process { StartInfo = psi })
                {
                    currentRunningProcess = proc;
                    proc.OutputDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) AppendLog(e.Data); };
                    proc.ErrorDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) AppendLog(e.Data); };

                    proc.Start();
                    proc.BeginOutputReadLine();
                    proc.BeginErrorReadLine();
                    proc.WaitForExit();
                    currentRunningProcess = null;
                    return proc.ExitCode;
                }
            });
        }

        private async Task<int> RunProcessDirectAsync(string exe, string args, string workingDir)
        {
            return await Task.Run(() =>
            {
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = exe,
                    Arguments = args,
                    WorkingDirectory = workingDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    StandardOutputEncoding = Encoding.UTF8,
                    StandardErrorEncoding = Encoding.UTF8,
                    CreateNoWindow = true
                };

                using (Process proc = new Process { StartInfo = psi })
                {
                    currentRunningProcess = proc;
                    proc.OutputDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) AppendLog(e.Data); };
                    proc.ErrorDataReceived += (s, e) => { if (!string.IsNullOrEmpty(e.Data)) AppendLog(e.Data); };

                    proc.Start();
                    proc.BeginOutputReadLine();
                    proc.BeginErrorReadLine();
                    proc.WaitForExit();
                    currentRunningProcess = null;
                    return proc.ExitCode;
                }
            });
        }
    }

    // =========================================================================
    // CONTROLES PERSONALIZADOS (DEEP DARK & NEON LIME)
    // =========================================================================
    public class RoundedButton : Button
    {
        public Color HoverColor { get; set; }
        public Color BorderColor { get; set; }
        public Color HoverBorderColor { get; set; }
        public Color HoverTextColor { get; set; }
        public int CornerRadius { get; set; }

        private bool isHovered = false;

        public RoundedButton()
        {
            this.HoverColor = Color.FromArgb(189, 224, 14);
            this.BorderColor = Color.FromArgb(30, 35, 48);
            this.HoverBorderColor = Color.FromArgb(170, 201, 12);
            this.HoverTextColor = Color.Black;
            this.CornerRadius = 6;
            this.FlatStyle = FlatStyle.Flat;
            this.FlatAppearance.BorderSize = 0;
            this.SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
            this.SetStyle(ControlStyles.Selectable, false);
        }

        protected override void OnMouseEnter(EventArgs e)
        {
            base.OnMouseEnter(e);
            isHovered = true;
            this.Invalidate();
        }

        protected override void OnMouseLeave(EventArgs e)
        {
            base.OnMouseLeave(e);
            isHovered = false;
            this.Invalidate();
        }

        protected override void OnPaintBackground(PaintEventArgs pevent)
        {
            Color parentBg = this.Parent != null ? this.Parent.BackColor : Color.FromArgb(16, 18, 24);
            using (SolidBrush parentBrush = new SolidBrush(parentBg))
            {
                pevent.Graphics.FillRectangle(parentBrush, this.ClientRectangle);
            }
        }

        protected override void OnPaint(PaintEventArgs pevent)
        {
            pevent.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            pevent.Graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;

            Color parentBg = this.Parent != null ? this.Parent.BackColor : Color.FromArgb(16, 18, 24);
            using (SolidBrush parentBrush = new SolidBrush(parentBg))
            {
                pevent.Graphics.FillRectangle(parentBrush, this.ClientRectangle);
            }

            Color bg = isHovered ? HoverColor : this.BackColor;
            Color border = isHovered ? HoverBorderColor : BorderColor;
            Color txtColor = isHovered ? HoverTextColor : this.ForeColor;

            RectangleF rect = new RectangleF(1f, 1f, this.Width - 2f, this.Height - 2f);
            using (GraphicsPath path = GetRoundPath(rect, CornerRadius))
            {
                using (SolidBrush brush = new SolidBrush(bg))
                {
                    pevent.Graphics.FillPath(brush, path);
                }

                if (border != Color.Transparent)
                {
                    using (Pen pen = new Pen(border, 1f))
                    {
                        pevent.Graphics.DrawPath(pen, path);
                    }
                }
            }

            TextRenderer.DrawText(
                pevent.Graphics,
                this.Text,
                this.Font,
                this.ClientRectangle,
                txtColor,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter
            );
        }

        private GraphicsPath GetRoundPath(RectangleF rect, float radius)
        {
            GraphicsPath path = new GraphicsPath();
            float r = radius;
            path.AddArc(rect.X, rect.Y, r, r, 180, 90);
            path.AddArc(rect.Right - r, rect.Y, r, r, 270, 90);
            path.AddArc(rect.Right - r, rect.Bottom - r, r, r, 0, 90);
            path.AddArc(rect.X, rect.Bottom - r, r, r, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    public class CustomProgressBar : Control
    {
        public Color ProgressColor { get; set; }
        public Color BackgroundColor { get; set; }
        public Color BorderColor { get; set; }

        private int val = 0;
        public int Value
        {
            get { return val; }
            set { val = Math.Max(0, Math.Min(100, value)); this.Invalidate(); }
        }

        public CustomProgressBar()
        {
            this.ProgressColor = Color.FromArgb(170, 201, 12);
            this.BackgroundColor = Color.FromArgb(6, 7, 9);
            this.BorderColor = Color.FromArgb(30, 35, 48);
            this.SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            using (GraphicsPath bgPath = GetRoundPath(new RectangleF(0, 0, this.Width, this.Height), 4))
            {
                using (SolidBrush bgBrush = new SolidBrush(BackgroundColor))
                {
                    e.Graphics.FillPath(bgBrush, bgPath);
                }
                using (Pen borderPen = new Pen(BorderColor, 1))
                {
                    e.Graphics.DrawPath(borderPen, bgPath);
                }
            }

            if (val > 0)
            {
                float w = (this.Width * (val / 100f));
                if (w > 4)
                {
                    using (GraphicsPath fillPath = GetRoundPath(new RectangleF(0, 0, w, this.Height), 4))
                    {
                        using (SolidBrush fillBrush = new SolidBrush(ProgressColor))
                        {
                            e.Graphics.FillPath(fillBrush, fillPath);
                        }
                    }
                }
            }
        }

        private GraphicsPath GetRoundPath(RectangleF rect, float radius)
        {
            GraphicsPath path = new GraphicsPath();
            float r = radius;
            path.AddArc(rect.X, rect.Y, r, r, 180, 90);
            path.AddArc(rect.Right - r, rect.Y, r, r, 270, 90);
            path.AddArc(rect.Right - r, rect.Bottom - r, r, r, 0, 90);
            path.AddArc(rect.X, rect.Bottom - r, r, r, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    public class CustomLogTextBox : RichTextBox
    {
        private const int WM_MOUSEWHEEL = 0x020A;
        private const int EM_LINESCROLL = 0x00B6;

        [DllImport("user32.dll", CharSet = CharSet.Auto)]
        public static extern IntPtr SendMessage(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);

        public Action OnScrolled;

        public CustomLogTextBox()
        {
            this.ScrollBars = RichTextBoxScrollBars.None;
            this.SetStyle(ControlStyles.OptimizedDoubleBuffer, true);
        }

        protected override void WndProc(ref Message m)
        {
            if (m.Msg == 0x204 || m.Msg == 0x205) return;
            if (m.Msg == WM_MOUSEWHEEL)
            {
                int delta = (short)((m.WParam.ToInt64() >> 16) & 0xFFFF);
                int lines = SystemInformation.MouseWheelScrollLines;
                if (lines <= 0) lines = 3;
                int scrollLines = (delta > 0) ? -lines : lines;
                SendMessage(this.Handle, EM_LINESCROLL, IntPtr.Zero, (IntPtr)scrollLines);
                if (OnScrolled != null) OnScrolled();
                return;
            }
            base.WndProc(ref m);
        }
    }

    public class DarkScrollBar : Control
    {
        private const int EM_GETFIRSTVISIBLELINE = 0x00CE;
        private const int EM_LINESCROLL = 0x00B6;

        private CustomLogTextBox targetTextBox;
        private bool isDragging = false;

        public DarkScrollBar()
        {
            this.SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
            this.BackColor = Color.FromArgb(6, 7, 9);
            this.Cursor = Cursors.Default;
        }

        public void BindTextBox(CustomLogTextBox tb)
        {
            this.targetTextBox = tb;
            if (tb != null)
            {
                tb.OnScrolled = () => this.Invalidate();
            }
        }

        public void SyncWithTextBox()
        {
            this.Invalidate();
        }

        protected override void OnMouseDown(MouseEventArgs e)
        {
            base.OnMouseDown(e);
            if (e.Button == MouseButtons.Left && targetTextBox != null)
            {
                isDragging = true;
                ScrollToMouse(e.Y);
            }
        }

        protected override void OnMouseMove(MouseEventArgs e)
        {
            base.OnMouseMove(e);
            if (isDragging && targetTextBox != null)
            {
                ScrollToMouse(e.Y);
            }
        }

        protected override void OnMouseUp(MouseEventArgs e)
        {
            base.OnMouseUp(e);
            isDragging = false;
        }

        private void ScrollToMouse(int mouseY)
        {
            if (targetTextBox == null || this.Height <= 0) return;
            int totalLines = Math.Max(1, targetTextBox.Lines.Length);
            float ratio = Math.Max(0f, Math.Min(1f, (float)mouseY / (float)this.Height));
            int targetLine = (int)(ratio * totalLines);
            int currentLine = CustomLogTextBox.SendMessage(targetTextBox.Handle, EM_GETFIRSTVISIBLELINE, IntPtr.Zero, IntPtr.Zero).ToInt32();
            int diff = targetLine - currentLine;
            if (diff != 0)
            {
                CustomLogTextBox.SendMessage(targetTextBox.Handle, EM_LINESCROLL, IntPtr.Zero, (IntPtr)diff);
                this.Invalidate();
            }
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            e.Graphics.Clear(this.BackColor);

            if (targetTextBox == null || targetTextBox.Lines.Length == 0)
            {
                using (SolidBrush thumb = new SolidBrush(Color.FromArgb(40, 48, 62)))
                {
                    e.Graphics.FillRectangle(thumb, 1, 4, this.Width - 2, this.Height - 8);
                }
                return;
            }

            int totalLines = Math.Max(1, targetTextBox.Lines.Length);
            int visibleLines = Math.Max(1, targetTextBox.Height / 14);
            int firstVisible = CustomLogTextBox.SendMessage(targetTextBox.Handle, EM_GETFIRSTVISIBLELINE, IntPtr.Zero, IntPtr.Zero).ToInt32();

            float viewRatio = Math.Min(1f, (float)visibleLines / (float)totalLines);
            int thumbHeight = Math.Max(24, (int)(this.Height * viewRatio));
            
            int maxScroll = Math.Max(1, totalLines - visibleLines);
            float scrollProgress = Math.Max(0f, Math.Min(1f, (float)firstVisible / (float)maxScroll));
            int thumbY = (int)(scrollProgress * (this.Height - thumbHeight));

            using (SolidBrush thumb = new SolidBrush(Color.FromArgb(55, 65, 85)))
            {
                using (GraphicsPath path = GetRoundPath(new RectangleF(1, thumbY, this.Width - 2, thumbHeight), 3))
                {
                    e.Graphics.FillPath(thumb, path);
                }
            }
        }

        private static GraphicsPath GetRoundPath(RectangleF rect, float radius)
        {
            GraphicsPath path = new GraphicsPath();
            float r = radius;
            path.AddArc(rect.X, rect.Y, r, r, 180, 90);
            path.AddArc(rect.Right - r, rect.Y, r, r, 270, 90);
            path.AddArc(rect.Right - r, rect.Bottom - r, r, r, 0, 90);
            path.AddArc(rect.X, rect.Bottom - r, r, r, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    public static class CustomDarkModal
    {
        public static void Show(IWin32Window owner, string title, string message, bool isError = false)
        {
            using (Form form = new Form())
            {
                form.FormBorderStyle = FormBorderStyle.None;
                form.StartPosition = FormStartPosition.CenterParent;
                form.Size = new Size(420, 190);
                form.BackColor = Color.FromArgb(10, 12, 16);
                form.ShowInTaskbar = false;

                Panel card = new Panel
                {
                    Location = new Point(14, 14),
                    Size = new Size(392, 162),
                    BackColor = Color.FromArgb(16, 18, 24)
                };

                Label lblTitle = new Label
                {
                    Text = title,
                    Font = new Font("Segoe UI", 11.5f, FontStyle.Bold),
                    ForeColor = isError ? Color.FromArgb(239, 68, 68) : Color.FromArgb(170, 201, 12),
                    Location = new Point(18, 16),
                    AutoSize = true
                };

                Label lblMsg = new Label
                {
                    Text = message,
                    Font = new Font("Segoe UI", 9.5f),
                    ForeColor = Color.White,
                    Location = new Point(18, 48),
                    Size = new Size(356, 60)
                };

                RoundedButton btnOk = new RoundedButton
                {
                    Text = "Aceptar",
                    Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                    ForeColor = Color.Black,
                    BackColor = Color.FromArgb(170, 201, 12),
                    HoverColor = Color.FromArgb(189, 224, 14),
                    Location = new Point(274, 116),
                    Size = new Size(100, 32),
                    Cursor = Cursors.Hand
                };
                btnOk.Click += (s, e) => form.Close();

                card.Controls.Add(lblTitle);
                card.Controls.Add(lblMsg);
                card.Controls.Add(btnOk);
                form.Controls.Add(card);

                form.ShowDialog(owner);
            }
        }
    }
}
