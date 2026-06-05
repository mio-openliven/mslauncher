using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;

internal static class Program
{
    private const string AppName = "MSLaunch";
    private const string ExeName = "MSLauncher.exe";
    private const string PackageName = "MSLaunchPayload.dat";
    private const string PackageSha256 = "d25fb662a47ea4ef346f680b2f4fd00c626a629edd2dfc48c8674e4ae07744ed";
    private const int ChunkSize = 262144;

    private static readonly string[] BootstrapManifests =
    {
        "https://mslaunch.186.246.12.238.sslip.io/downloads/bootstrap.json",
        "https://github.com/mio-openliven/MSNukem/releases/download/v1.9.0-beta.1/bootstrap.json",
    };

    [STAThread]
    private static void Main()
    {
        ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072;
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new SetupForm());
    }

    private sealed class SetupForm : Form
    {
        private readonly Label statusLabel;
        private readonly Label detailLabel;
        private readonly ProgressBar progressBar;
        private readonly Button closeButton;

        public SetupForm()
        {
            Text = "MSLaunch Setup";
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            MinimizeBox = true;
            StartPosition = FormStartPosition.CenterScreen;
            ClientSize = new System.Drawing.Size(430, 155);
            Font = new System.Drawing.Font("Segoe UI", 9F);

            var title = new Label
            {
                Text = AppName,
                Left = 18,
                Top = 16,
                Width = 380,
                Height = 28,
                Font = new System.Drawing.Font("Segoe UI", 16F, System.Drawing.FontStyle.Bold),
            };
            statusLabel = new Label { Left = 20, Top = 58, Width = 390, Height = 20, Text = "Подготовка..." };
            progressBar = new ProgressBar { Left = 20, Top = 84, Width = 390, Height = 20 };
            detailLabel = new Label { Left = 20, Top = 111, Width = 390, Height = 18, ForeColor = System.Drawing.Color.DimGray };
            closeButton = new Button { Text = "Закрыть", Left = 318, Top = 123, Width = 92, Height = 26, Enabled = false };
            closeButton.Click += (sender, args) => Close();

            Controls.Add(title);
            Controls.Add(statusLabel);
            Controls.Add(progressBar);
            Controls.Add(detailLabel);
            Controls.Add(closeButton);
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            Task.Run(() => RunInstall());
        }

        private void RunInstall()
        {
            try
            {
                Installer.Install(this);
                SetProgress(100);
                SetText("Готово.", "Лаунчер запускается...");
                Thread.Sleep(1200);
                BeginInvoke((Action)Close);
            }
            catch (Exception ex)
            {
                SetText("Не удалось установить MSLaunch.", ex.Message);
                BeginInvoke((Action)(() => closeButton.Enabled = true));
            }
        }

        public void SetProgress(int value)
        {
            BeginInvoke((Action)(() => progressBar.Value = Math.Max(0, Math.Min(100, value))));
        }

        public void SetText(string status, string detail)
        {
            BeginInvoke((Action)(() =>
            {
                statusLabel.Text = status;
                detailLabel.Text = detail ?? "";
            }));
        }
    }

    private static class Installer
    {
        public static void Install(SetupForm ui)
        {
            var localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var installRoot = Path.Combine(localAppData, "MSLaunch", "Launcher");
            var userConfigPath = Path.Combine(appData, "MSLauncher", "launcher_config.json");
            var shortcutPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "MSLaunch.lnk");

            ui.SetText("Выбор быстрого источника...", "Проверяем хост и GitHub");
            var sources = LoadSources();
            var errors = new List<string>();
            var tempDir = Path.Combine(Path.GetTempPath(), "mslaunch-setup-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempDir);
            var archivePath = Path.Combine(tempDir, PackageName);

            try
            {
                foreach (var source in sources)
                {
                    try
                    {
                        ui.SetProgress(0);
                        ui.SetText("Скачивание лаунчера...", "Источник: " + source.Name);
                        DownloadFile(ui, source.Url, archivePath);
                        var actualHash = Sha256(archivePath);
                        if (!String.Equals(actualHash, source.Sha256, StringComparison.OrdinalIgnoreCase))
                        {
                            throw new InvalidOperationException("Проверка SHA256 не совпала.");
                        }
                        ExtractPackage(ui, archivePath, installRoot);
                        var exePath = Path.Combine(installRoot, ExeName);
                        if (!File.Exists(exePath))
                        {
                            throw new FileNotFoundException("MSLauncher.exe не найден после распаковки.");
                        }
                        ui.SetProgress(92);
                        ui.SetText("Обновление настроек...", userConfigPath);
                        UpdateUserConfig(installRoot, userConfigPath);
                        ui.SetText("Создание ярлыка...", shortcutPath);
                        CreateShortcut(shortcutPath, exePath, installRoot);
                        Process.Start(new ProcessStartInfo { FileName = exePath, WorkingDirectory = installRoot });
                        return;
                    }
                    catch (Exception ex)
                    {
                        errors.Add(source.Name + ": " + ex.Message);
                        TryDeleteFile(archivePath);
                    }
                }
            }
            finally
            {
                TryDeleteDirectory(tempDir);
            }

            throw new InvalidOperationException(String.Join("; ", errors.ToArray()));
        }

        private static List<Source> LoadSources()
        {
            foreach (var manifestUrl in BootstrapManifests)
            {
                try
                {
                    var parsed = ParseBootstrap(DownloadString(manifestUrl));
                    if (parsed.Count > 0)
                    {
                        return parsed;
                    }
                }
                catch
                {
                }
            }

            return new List<Source>
            {
                new Source("Host", "https://mslaunch.186.246.12.238.sslip.io/downloads/" + PackageName, PackageSha256),
                new Source("GitHub", "https://github.com/mio-openliven/MSNukem/releases/download/v1.9.0-beta.1/MSLaunchPayload.dat", PackageSha256),
            };
        }

        private static List<Source> ParseBootstrap(string json)
        {
            var result = new List<Source>();
            var root = new JavaScriptSerializer().DeserializeObject(json) as Dictionary<string, object>;
            if (root == null || !root.ContainsKey("sources"))
            {
                return result;
            }
            var sources = root["sources"] as ArrayList;
            if (sources == null)
            {
                return result;
            }
            foreach (var item in sources)
            {
                var source = item as Dictionary<string, object>;
                if (source == null)
                {
                    continue;
                }
                var name = Convert.ToString(source.ContainsKey("name") ? source["name"] : "Source");
                var url = Convert.ToString(source.ContainsKey("url") ? source["url"] : "");
                var sha = Convert.ToString(source.ContainsKey("sha256") ? source["sha256"] : "").ToLowerInvariant();
                if (url.StartsWith("https://", StringComparison.OrdinalIgnoreCase) && sha.Length == 64)
                {
                    result.Add(new Source(name, url, sha));
                }
            }
            return result;
        }

        private static string DownloadString(string url)
        {
            using (var client = NewClient())
            {
                return client.DownloadString(url);
            }
        }

        private static void DownloadFile(SetupForm ui, string url, string target)
        {
            var request = (HttpWebRequest)WebRequest.Create(url);
            request.UserAgent = "MSLaunchSetup/1.2";
            request.Timeout = 30000;
            using (var response = (HttpWebResponse)request.GetResponse())
            using (var input = response.GetResponseStream())
            using (var output = File.Create(target))
            {
                var total = response.ContentLength;
                long done = 0;
                var buffer = new byte[ChunkSize];
                while (true)
                {
                    var read = input.Read(buffer, 0, buffer.Length);
                    if (read <= 0)
                    {
                        break;
                    }
                    output.Write(buffer, 0, read);
                    done += read;
                    if (total > 0)
                    {
                        ui.SetProgress((int)(done * 75 / total));
                        ui.SetText("Скачивание лаунчера...", String.Format("{0} / {1} MB", done / 1024 / 1024, Math.Max(1, total / 1024 / 1024)));
                    }
                }
            }
        }

        private static string Sha256(string path)
        {
            using (var sha = SHA256.Create())
            using (var stream = File.OpenRead(path))
            {
                var hash = sha.ComputeHash(stream);
                var builder = new StringBuilder(hash.Length * 2);
                foreach (var value in hash)
                {
                    builder.Append(value.ToString("x2"));
                }
                return builder.ToString();
            }
        }

        private static void ExtractPackage(SetupForm ui, string archivePath, string installRoot)
        {
            ui.SetText("Распаковка...", installRoot);
            var staging = installRoot + ".staging";
            TryDeleteDirectory(staging);
            Directory.CreateDirectory(staging);
            ZipFile.ExtractToDirectory(archivePath, staging);
            TryDeleteDirectory(installRoot);
            Directory.CreateDirectory(Path.GetDirectoryName(installRoot));
            Directory.Move(staging, installRoot);
        }

        private static void UpdateUserConfig(string installRoot, string userConfigPath)
        {
            var bundledPath = Path.Combine(installRoot, "launcher_config.json");
            if (!File.Exists(bundledPath))
            {
                return;
            }
            var bundled = ReadJsonObject(bundledPath);
            var current = ReadJsonObject(userConfigPath);
            var merged = new Dictionary<string, object>(bundled);
            foreach (var key in new[] { "game_directory", "profiles_directory", "default_profile", "default_username", "recent_usernames", "skin_path", "launch" })
            {
                if (current.ContainsKey(key))
                {
                    merged[key] = current[key];
                }
            }
            foreach (var key in new[] { "panel", "builds", "default_build", "client_mode", "default_language", "project_access", "support_url", "support_urls", "admin_links", "social_links", "news" })
            {
                if (bundled.ContainsKey(key))
                {
                    merged[key] = bundled[key];
                }
            }

            Directory.CreateDirectory(Path.GetDirectoryName(userConfigPath));
            if (File.Exists(userConfigPath))
            {
                var backupName = "launcher_config.before-setup-" + DateTimeOffset.UtcNow.ToUnixTimeSeconds() + ".json";
                File.Copy(userConfigPath, Path.Combine(Path.GetDirectoryName(userConfigPath), backupName), true);
            }
            File.WriteAllText(userConfigPath, new JavaScriptSerializer().Serialize(merged), Encoding.UTF8);
        }

        private static Dictionary<string, object> ReadJsonObject(string path)
        {
            if (!File.Exists(path))
            {
                return new Dictionary<string, object>();
            }
            try
            {
                return new JavaScriptSerializer().DeserializeObject(File.ReadAllText(path, Encoding.UTF8)) as Dictionary<string, object>
                    ?? new Dictionary<string, object>();
            }
            catch
            {
                return new Dictionary<string, object>();
            }
        }

        private static WebClient NewClient()
        {
            var client = new WebClient();
            client.Headers[HttpRequestHeader.UserAgent] = "MSLaunchSetup/1.2";
            client.Encoding = Encoding.UTF8;
            return client;
        }

        private static void CreateShortcut(string shortcutPath, string exePath, string workingDirectory)
        {
            var shellType = Type.GetTypeFromProgID("WScript.Shell");
            if (shellType == null)
            {
                return;
            }
            var shell = Activator.CreateInstance(shellType);
            var shortcut = shellType.InvokeMember("CreateShortcut", BindingFlags.InvokeMethod, null, shell, new object[] { shortcutPath });
            var shortcutType = shortcut.GetType();
            shortcutType.InvokeMember("TargetPath", BindingFlags.SetProperty, null, shortcut, new object[] { exePath });
            shortcutType.InvokeMember("WorkingDirectory", BindingFlags.SetProperty, null, shortcut, new object[] { workingDirectory });
            shortcutType.InvokeMember("IconLocation", BindingFlags.SetProperty, null, shortcut, new object[] { exePath + ",0" });
            shortcutType.InvokeMember("Save", BindingFlags.InvokeMethod, null, shortcut, null);
        }

        private static void TryDeleteFile(string path)
        {
            try
            {
                if (File.Exists(path))
                {
                    File.Delete(path);
                }
            }
            catch
            {
            }
        }

        private static void TryDeleteDirectory(string path)
        {
            try
            {
                if (Directory.Exists(path))
                {
                    Directory.Delete(path, true);
                }
            }
            catch
            {
            }
        }
    }

    private sealed class Source
    {
        public Source(string name, string url, string sha256)
        {
            Name = String.IsNullOrWhiteSpace(name) ? "Source" : name;
            Url = url;
            Sha256 = sha256;
        }

        public string Name { get; private set; }
        public string Url { get; private set; }
        public string Sha256 { get; private set; }
    }
}
