param([int]$Passes = 2, [string]$BuildDirectory = (Join-Path (Split-Path $PSScriptRoot) 'build\sets'), [string[]]$DocumentBases = @('sets'), [ValidateRange(1,60000)][int]$MutexTimeoutMs = 1000)
$ErrorActionPreference = 'Stop'
$taskBuild = [System.IO.Path]::GetFullPath($BuildDirectory)
foreach($taskBase in $DocumentBases) { if($taskBase -notmatch '^[a-zA-Z0-9-]+$') { throw 'Invalid document base' } }
if(Test-Path -LiteralPath (Join-Path $taskBuild 'TEX_RECEIPT.json')) {
    $taskHistory=Join-Path $taskBuild 'tex-history'
    New-Item -ItemType Directory -Path $taskHistory -Force | Out-Null
    $taskPriorHash=(Get-FileHash -LiteralPath (Join-Path $taskBuild 'TEX_RECEIPT.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath (Join-Path $taskBuild 'TEX_RECEIPT.json') -Destination (Join-Path $taskHistory "$taskPriorHash.json")
}
$taskOldEpoch = $env:SOURCE_DATE_EPOCH
$taskOldForce = $env:FORCE_SOURCE_DATE
$taskMutex = New-Object System.Threading.Mutex($false, 'Global\InterlanguageTeXSlotV1')
$taskAcquired = $false
$taskAbandoned = $false
$taskReceipt = [ordered]@{ schema='ps-guarded-tex/1'; mutex='Global\InterlanguageTeXSlotV1'; timeout_ms=$MutexTimeoutMs; acquired=$false; abandoned_recovered=$false; passes=@(); log_checks=@(); status='not-started' }
try {
    try { $taskAcquired = $taskMutex.WaitOne($MutexTimeoutMs) } catch [System.Threading.AbandonedMutexException] { $taskAcquired=$true; $taskAbandoned=$true }
    $taskReceipt.acquired=$taskAcquired
    $taskReceipt.abandoned_recovered=$taskAbandoned
    if (-not $taskAcquired) { $taskReceipt.status='slot-unavailable'; return }
    $env:SOURCE_DATE_EPOCH = '1788480000'
    $env:FORCE_SOURCE_DATE = '1'
    Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Threading;
public static class PsGuardedTex {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct STARTUPINFO { public int cb; public string reserved,desktop,title; public int x,y,xsize,ysize,xchars,ychars,fill,flags; public short show,reserved2; public IntPtr reservedptr,stdin,stdout,stderr; }
 [StructLayout(LayoutKind.Sequential)] struct PROCESS_INFORMATION { public IntPtr process,thread; public uint pid,tid; }
 [StructLayout(LayoutKind.Sequential)] struct ACCOUNT { public long user,kernel,perioduser,periodkernel; public uint faults,total,active,terminated; }
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder cmd,IntPtr pa,IntPtr ta,bool inherit,uint flags,IntPtr env,string dir,ref STARTUPINFO si,out PROCESS_INFORMATION pi);
 [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr attr,string name);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
 [DllImport("kernel32.dll")] static extern uint ResumeThread(IntPtr thread);
 [DllImport("kernel32.dll")] static extern bool QueryInformationJobObject(IntPtr job,int cls,out ACCOUNT info,int size,IntPtr length);
 [DllImport("kernel32.dll")] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
 [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle,uint timeout);
 [DllImport("kernel32.dll")] static extern bool TerminateJobObject(IntPtr job,uint code);
 [DllImport("kernel32.dll")] static extern bool TerminateProcess(IntPtr process,uint code);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 public static uint Run(string exe,string args,string cwd,int seconds) {
  IntPtr job=CreateJobObject(IntPtr.Zero,null); if(job==IntPtr.Zero) throw new Exception("Job creation failed");
  PROCESS_INFORMATION pi=new PROCESS_INFORMATION(); bool assigned=false;
  try {
   STARTUPINFO si=new STARTUPINFO(); si.cb=Marshal.SizeOf(si);
   if(!CreateProcess(exe,new StringBuilder("\""+exe+"\" "+args),IntPtr.Zero,IntPtr.Zero,false,0x08000004,IntPtr.Zero,cwd,ref si,out pi)) throw new Exception("CreateProcess failed: "+Marshal.GetLastWin32Error());
   if(!AssignProcessToJobObject(job,pi.process)) {TerminateProcess(pi.process,91); WaitForSingleObject(pi.process,10000); throw new Exception("Capture failed; suspended process stopped");}
   assigned=true;
   if(ResumeThread(pi.thread)==0xffffffff) throw new Exception("Resume failed");
   DateTime until=DateTime.UtcNow.AddSeconds(seconds);
   while(true) {
    ACCOUNT a;
    if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero)) throw new Exception("Captured-tree query failed");
    if(a.active==0) break;
    if(DateTime.UtcNow>until) throw new Exception("Captured-tree runtime exceeded");
    Thread.Sleep(100);
   }
   uint code; GetExitCodeProcess(pi.process,out code); return code;
  } finally {
   if(assigned) {
    ACCOUNT a;
    if(QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero) && a.active!=0) {
     TerminateJobObject(job,92);
     do {Thread.Sleep(100); if(!QueryInformationJobObject(job,1,out a,Marshal.SizeOf(typeof(ACCOUNT)),IntPtr.Zero)) throw new Exception("Cannot verify captured-tree termination");} while(a.active!=0);
    }
   }
   if(pi.thread!=IntPtr.Zero)CloseHandle(pi.thread);
   if(pi.process!=IntPtr.Zero)CloseHandle(pi.process);
   CloseHandle(job);
  }
 }
}
'@
    $taskEngine = (Get-Command xelatex.exe).Source
    foreach($taskBase in $DocumentBases) {
      for($taskPass=1;$taskPass -le $Passes;$taskPass++) {
        $taskCode = [PsGuardedTex]::Run($taskEngine, "-no-shell-escape -interaction=nonstopmode -halt-on-error $taskBase.tex", $taskBuild, 180)
        $taskReceipt.passes += @{document=$taskBase;pass=$taskPass;exit_code=$taskCode;captured_job_active_processes_after=0}
        $taskLog = Get-Content -LiteralPath (Join-Path $taskBuild "$taskBase.log") -Raw
        $taskFindings = @($taskLog -split "`n" | Where-Object { $_ -match 'Missing character|^!|Overfull|undefined|Rerun to get' })
        $taskReceipt.log_checks += @{document=$taskBase;pass=$taskPass;findings=$taskFindings}
        if(Test-Path -LiteralPath (Join-Path $taskBuild "$taskBase.pdf")) {
            $taskReceipt.passes[-1].pdf_sha256=(Get-FileHash -LiteralPath (Join-Path $taskBuild "$taskBase.pdf") -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        if($taskCode -ne 0) { throw "TeX pass $taskPass failed with exit code $taskCode" }
      }
    }
    $taskReceipt.status='processes-completed'
} catch {
    $taskReceipt.status='failed'
    $taskReceipt.error=$_.Exception.Message
} finally {
    $taskReceipt.completed_utc=[DateTime]::UtcNow.ToString('o')
    $taskReceipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $taskBuild 'TEX_RECEIPT.json') -Encoding utf8
    if($taskAcquired) { $taskMutex.ReleaseMutex() }
    $taskMutex.Dispose()
    $env:SOURCE_DATE_EPOCH=$taskOldEpoch
    $env:FORCE_SOURCE_DATE=$taskOldForce
}
$taskReceipt | ConvertTo-Json -Depth 8
