using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

class NotesDemo : Form {
    private TextBox input;
    private Label status;
    [STAThread]
    static void Main(string[] args) {
        if (args.Length == 2 && args[0] == "--install-to") {
            Directory.CreateDirectory(args[1]);
            File.Copy(Application.ExecutablePath, Path.Combine(args[1], "ProoflaneNotes.exe"), true);
            return;
        }
        if (args.Length == 1 && args[0] == "--exit-error") {
            Environment.Exit(42);
        }
        Application.EnableVisualStyles();
        Application.Run(new NotesDemo());
    }
    NotesDemo() {
        Text = "Prooflane Notes";
        Size = new Size(740, 510);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(246, 248, 252);
        Font = new Font("Segoe UI", 11);
        var brand = new Label { Text = "PROOFLANE / NOTES", Location = new Point(40, 35), AutoSize = true, ForeColor = Color.FromArgb(83, 96, 210) };
        var heading = new Label { Text = "A small note. A real Windows test.", Location = new Point(40, 80), AutoSize = true, Font = new Font("Segoe UI", 19, FontStyle.Bold) };
        var hint = new Label { Text = "Write something below, then save it to this session.", Location = new Point(40, 133), AutoSize = true, ForeColor = Color.DimGray };
        input = new TextBox { Name = "noteInput", AccessibleName = "Note", Location = new Point(44, 191), Size = new Size(635, 90), Multiline = true };
        var save = new Button { Name = "saveButton", Text = "Save note", Location = new Point(44, 305), Size = new Size(155, 45), BackColor = Color.FromArgb(83, 96, 210), ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
        status = new Label { Name = "statusLabel", Text = "Ready to write", Location = new Point(44, 380), Size = new Size(630, 45), ForeColor = Color.FromArgb(35, 135, 99) };
        save.Click += delegate { status.Text = "Saved: " + input.Text; };
        Controls.AddRange(new Control[] { brand, heading, hint, input, save, status });
    }
}
