using System;
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Interop;
using System.Windows.Media;

namespace GeoStudio.UI.Services;

/// <summary>
/// Reusable helper to streamline native Color Dialog prompts,
/// eliminating duplicate P/Invoke declarations across windows.
/// </summary>
public static class ColorDialogHelper
{
    [StructLayout(LayoutKind.Sequential)]
    private struct CHOOSECOLOR
    {
        public int lStructSize;
        public IntPtr hwndOwner;
        public IntPtr hInstance;
        public int rgbResult;
        public IntPtr lpCustColors;
        public int Flags;
        public IntPtr lCustData;
        public IntPtr lpfnHook;
        public IntPtr lpTemplateName;
    }

    [DllImport("comdlg32.dll", SetLastError = true)]
    private static extern bool ChooseColor(ref CHOOSECOLOR cc);

    private static readonly int[] _customColors = new int[16];

    public static string? PromptColorHex(string? initialHex = null, Window? owner = null)
    {
        byte r = 59, g = 130, b = 246;
        if (!string.IsNullOrEmpty(initialHex))
        {
            try
            {
                var c = (Color)ColorConverter.ConvertFromString(initialHex);
                r = c.R; g = c.G; b = c.B;
            }
            catch { }
        }

        var cc = new CHOOSECOLOR();
        cc.lStructSize = Marshal.SizeOf(cc);
        if (owner != null)
        {
            try
            {
                var helper = new WindowInteropHelper(owner);
                cc.hwndOwner = helper.Handle;
            }
            catch { }
        }
        cc.rgbResult = r | (g << 8) | (b << 16);
        cc.Flags = 0x00000001 | 0x00000002;

        var handle = GCHandle.Alloc(_customColors, GCHandleType.Pinned);
        try
        {
            cc.lpCustColors = handle.AddrOfPinnedObject();
            if (ChooseColor(ref cc))
            {
                byte nr = (byte)(cc.rgbResult & 0xFF);
                byte ng = (byte)((cc.rgbResult >> 8) & 0xFF);
                byte nb = (byte)((cc.rgbResult >> 16) & 0xFF);
                return $"#{nr:X2}{ng:X2}{nb:X2}";
            }
        }
        finally
        {
            handle.Free();
        }
        return null;
    }
}
