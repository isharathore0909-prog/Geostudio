using System.IO;
using System.Windows.Controls;
using Microsoft.Win32;

namespace GeoStudio.UI.Services;

/// <summary>
/// Reusable helper to streamline OpenFileDialog and SaveFileDialog prompts across UI windows,
/// reducing repetitive boilerplate.
/// </summary>
public static class FileDialogHelper
{
    public static string? PromptOpen(string filter, string title = "Select File", string? initialDirectory = null)
    {
        var dlg = new OpenFileDialog
        {
            Filter = filter,
            Title = title,
            InitialDirectory = initialDirectory ?? string.Empty
        };
        return dlg.ShowDialog() == true ? dlg.FileName : null;
    }

    public static string[]? PromptOpenMultiple(string filter, string title = "Select Files", string? initialDirectory = null)
    {
        var dlg = new OpenFileDialog
        {
            Filter = filter,
            Title = title,
            Multiselect = true,
            InitialDirectory = initialDirectory ?? string.Empty
        };
        return dlg.ShowDialog() == true ? dlg.FileNames : null;
    }

    public static string? PromptOpenInto(TextBox targetBox, string filter, string title = "Select File")
    {
        string? path = PromptOpen(filter, title);
        if (path != null) targetBox.Text = path;
        return path;
    }

    public static string? PromptSave(string filter, string defaultFileName = "", string title = "Save File")
    {
        var dlg = new SaveFileDialog
        {
            Filter = filter,
            Title = title,
            FileName = defaultFileName
        };
        return dlg.ShowDialog() == true ? dlg.FileName : null;
    }

    public static string? PromptSaveInto(TextBox targetBox, string filter, string defaultFileName = "", string title = "Save File")
    {
        string initialName = string.IsNullOrEmpty(defaultFileName) ? Path.GetFileName(targetBox.Text) : defaultFileName;
        string? path = PromptSave(filter, initialName, title);
        if (path != null) targetBox.Text = path;
        return path;
    }
}
