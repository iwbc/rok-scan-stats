# PowerShell起動とウィンドウサイズ調整、autocap.py実行までする面倒くさがり向けスクリプト
# 3デバイス並列処理用

param([String]$dir = (Get-Date -Format "yyyy-MM-dd"))

$p1 = Start-Process -FilePath powershell.exe -PassThru -ArgumentList "-noexit -command python autocap.py 127.0.0.1:5745 -d $dir -s 1   -e 333"
$p2 = Start-Process -FilePath powershell.exe -PassThru -ArgumentList "-noexit -command python autocap.py 127.0.0.1:5755 -d $dir -s 334 -e 666"
$p3 = Start-Process -FilePath powershell.exe -PassThru -ArgumentList "-noexit -command python autocap.py 127.0.0.1:5765 -d $dir -s 667 -e 1000"

$w = 640
$h = 300
$x = 0
$y = 400

Add-Type @"
  using System;
  using System.Runtime.InteropServices;
  public class Win32Api {
    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
  }
"@

foreach ($p in $p1,$p2,$p3) {
  [Win32Api]::MoveWindow($p.MainWindowHandle, $x, $y, $w, $h, $true) | Out-Null
  $x = $x + $w
}
