using System;
using System.IO;
using System.IO.Compression;
using System.Diagnostics;
using System.Windows.Forms;
using System.Reflection;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;

namespace Voizy
{
    static class Program
    {
        [DllImport("shell32.dll", SetLastError = true)]
        public static extern void SetCurrentProcessExplicitAppUserModelID([MarshalAs(UnmanagedType.LPWStr)] string AppID);

        private const int BufferSize = 65536; // 64 KB buffer para máxima tasa de transferencia I/O

        [STAThread]
        static int Main(string[] args)
        {
            try
            {
                SetCurrentProcessExplicitAppUserModelID("Voizy.Studio.App");
            }
            catch { }

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string appDir = Path.Combine(localAppData, "Voizy", "app");
            string exePath = Path.Combine(appDir, "Voizy.exe");
            string versionFile = Path.Combine(appDir, ".version");

            // Obtener versión y firma del ensamblado compilado
            Assembly asm = Assembly.GetExecutingAssembly();
            string mvid = asm.ManifestModule.ModuleVersionId.ToString("N").Substring(0, 12);

            try
            {
                // Si el motor ya está desplegado e íntegro con la misma versión compilada, saltar extracción (<10ms)
                if (File.Exists(exePath) && File.Exists(versionFile) && File.ReadAllText(versionFile).Trim() == mvid &&
                    (File.Exists(Path.Combine(appDir, "_internal", "python312.dll")) || File.Exists(Path.Combine(appDir, "python312.dll"))))
                {
                    ProcessStartInfo psiFast = new ProcessStartInfo
                    {
                        FileName = exePath,
                        WorkingDirectory = appDir,
                        Arguments = string.Join(" ", args),
                        UseShellExecute = true
                    };
                    Process.Start(psiFast);
                    return 0;
                }

                // Primera ejecución o actualización de build: Mostrar Splash de Inicio
                SplashForm splash = new SplashForm();
                splash.Show();
                Application.DoEvents();

                if (Directory.Exists(appDir))
                {
                    try { Directory.Delete(appDir, true); } catch { }
                }
                Directory.CreateDirectory(appDir);

                Stream stream = asm.GetManifestResourceStream("payload.zip");
                if (stream == null)
                {
                    foreach (string name in asm.GetManifestResourceNames())
                    {
                        if (name.EndsWith("payload.zip", StringComparison.OrdinalIgnoreCase))
                        {
                            stream = asm.GetManifestResourceStream(name);
                            break;
                        }
                    }
                }

                if (stream == null)
                {
                    splash.Close();
                    MessageBox.Show("Error: No se encontró el paquete de recursos interno 'payload.zip'.", "Voizy Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return 1;
                }

                byte[] buffer = new byte[BufferSize];

                using (ZipArchive archive = new ZipArchive(stream, ZipArchiveMode.Read))
                {
                    int totalEntries = archive.Entries.Count;
                    int count = 0;

                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        string relPath = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                        string fullPath = Path.Combine(appDir, relPath);

                        // Protección Zip Slip
                        if (!Path.GetFullPath(fullPath).StartsWith(Path.GetFullPath(appDir) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        string dir = Path.GetDirectoryName(fullPath);
                        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                        {
                            Directory.CreateDirectory(dir);
                        }

                        if (!string.IsNullOrEmpty(entry.Name))
                        {
                            using (Stream entryStream = entry.Open())
                            using (FileStream fs = new FileStream(fullPath, FileMode.Create, FileAccess.Write, FileShare.None, BufferSize, FileOptions.SequentialScan))
                            {
                                int bytesRead;
                                while ((bytesRead = entryStream.Read(buffer, 0, buffer.Length)) > 0)
                                {
                                    fs.Write(buffer, 0, bytesRead);
                                }
                            }
                        }

                        count++;
                        if (count % 30 == 0 || count == totalEntries)
                        {
                            int pct = (int)((count / (double)totalEntries) * 100);
                            splash.UpdateProgress(pct, string.Format("Iniciando Voizy Studio... {0}%", pct));
                            Application.DoEvents();
                        }
                    }
                }

                // Guardar firma de versión desplegada
                try { File.WriteAllText(versionFile, mvid); } catch { }

                splash.Close();

                // Lanzamiento del proceso nativo directamente en la sesión interactiva
                ProcessStartInfo psi = new ProcessStartInfo
                {
                    FileName = exePath,
                    WorkingDirectory = appDir,
                    Arguments = string.Join(" ", args),
                    UseShellExecute = true
                };

                Process.Start(psi);
                return 0;
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error al iniciar Voizy Studio:\n\n" + ex.Message, "Voizy Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return 1;
            }
        }
    }

    public class SplashForm : Form
    {
        private ProgressBar pBar;
        private Label lblMsg;
        private PictureBox picLogo;

        public SplashForm()
        {
            this.FormBorderStyle = FormBorderStyle.None;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Size = new Size(390, 115);
            this.BackColor = Color.FromArgb(10, 12, 16);
            this.ForeColor = Color.White;
            this.TopMost = true;
            this.ShowInTaskbar = false;

            picLogo = new PictureBox
            {
                Location = new Point(18, 12),
                Size = new Size(28, 28),
                SizeMode = PictureBoxSizeMode.Zoom
            };
            try
            {
                Assembly asm = Assembly.GetExecutingAssembly();
                Stream icoStream = null;
                Stream logoStream = null;

                foreach (string name in asm.GetManifestResourceNames())
                {
                    if (name.EndsWith("voizy.ico", StringComparison.OrdinalIgnoreCase) || name.EndsWith("app.ico", StringComparison.OrdinalIgnoreCase))
                    {
                        icoStream = asm.GetManifestResourceStream(name);
                    }
                    else if (name.EndsWith("voizy_logo.png", StringComparison.OrdinalIgnoreCase) || name.EndsWith("logo.png", StringComparison.OrdinalIgnoreCase))
                    {
                        logoStream = asm.GetManifestResourceStream(name);
                    }
                }

                if (icoStream != null)
                {
                    try
                    {
                        Icon ic = new Icon(icoStream, 48, 48);
                        this.Icon = ic;
                        picLogo.Image = ic.ToBitmap();
                    }
                    catch { }
                }
                
                if (picLogo.Image == null && logoStream != null)
                {
                    try { picLogo.Image = Image.FromStream(logoStream); } catch { }
                }

                if (picLogo.Image == null)
                {
                    try
                    {
                        Icon appIcon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
                        if (appIcon != null)
                        {
                            this.Icon = appIcon;
                            picLogo.Image = appIcon.ToBitmap();
                        }
                    }
                    catch { }
                }
            }
            catch { }

            Label lblTitle = new Label
            {
                Text = "VOIZY STUDIO",
                Font = new Font("Segoe UI", 11.5f, FontStyle.Bold),
                ForeColor = Color.FromArgb(170, 201, 12),
                Location = new Point(54, 15),
                AutoSize = true
            };

            lblMsg = new Label
            {
                Text = "Preparando entorno ultra-rápido...",
                Font = new Font("Segoe UI", 8.5f),
                ForeColor = Color.FromArgb(156, 163, 175),
                Location = new Point(20, 50),
                Size = new Size(350, 18)
            };

            pBar = new ProgressBar
            {
                Location = new Point(20, 74),
                Size = new Size(350, 6),
                Style = ProgressBarStyle.Continuous
            };

            this.Controls.Add(picLogo);
            this.Controls.Add(lblTitle);
            this.Controls.Add(lblMsg);
            this.Controls.Add(pBar);

            this.Paint += (s, e) =>
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                using (Pen p = new Pen(Color.FromArgb(30, 35, 48), 1))
                {
                    e.Graphics.DrawRectangle(p, 0, 0, this.Width - 1, this.Height - 1);
                }
            };
        }

        public void UpdateProgress(int val, string message)
        {
            pBar.Value = Math.Max(0, Math.Min(100, val));
            lblMsg.Text = message;
        }
    }
}
