param(
  [string]$BaseUrl = "http://192.168.55.12:8099",
  [string]$StartPath = "/",
  [string]$OnlyRoute = "",
  [int]$DebugPort = 9223,
  [string]$OutPath = "frontend-performance-audit-events.json"
)

$ErrorActionPreference = "Stop"

$startUrl = $BaseUrl.TrimEnd("/") + "/" + $StartPath.TrimStart("/")
if ($startUrl.Contains("?")) {
  $startUrl = $startUrl + "&perfAudit=1"
} else {
  $startUrl = $startUrl + "?perfAudit=1"
}
$target = Invoke-RestMethod -Method Put ("http://127.0.0.1:$DebugPort/json/new?" + [uri]::EscapeDataString($startUrl))
$wsUri = [Uri]$target.webSocketDebuggerUrl
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$ws.ConnectAsync($wsUri, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
$id = 0

function Send-Cdp($method, $params = $null) {
  $script:id += 1
  $msg = @{ id = $script:id; method = $method }
  if ($null -ne $params) {
    $msg.params = $params
  }
  $json = $msg | ConvertTo-Json -Depth 20 -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $segment = [ArraySegment[byte]]::new($bytes)
  $script:ws.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).GetAwaiter().GetResult()

  while ($true) {
    $chunks = [System.Collections.Generic.List[string]]::new()
    do {
      $buffer = New-Object byte[] 1048576
      $out = [ArraySegment[byte]]::new($buffer)
      $result = $script:ws.ReceiveAsync($out, [Threading.CancellationToken]::None).GetAwaiter().GetResult()
      $chunks.Add([Text.Encoding]::UTF8.GetString($buffer, 0, $result.Count))
    } while (-not $result.EndOfMessage)
    $text = [string]::Concat($chunks)
    if ([string]::IsNullOrWhiteSpace($text)) {
      continue
    }
    $obj = $text | ConvertFrom-Json
    if ($obj.id -eq $script:id) {
      return $obj
    }
  }
}

function Eval-Js($expression, [int]$timeoutMs = 120000) {
  $response = Send-Cdp "Runtime.evaluate" @{
    expression = $expression
    awaitPromise = $true
    returnByValue = $true
    timeout = $timeoutMs
  }
  if ($response.result.exceptionDetails) {
    throw ($response.result.exceptionDetails | ConvertTo-Json -Depth 10)
  }
  return $response.result.result.value
}

function Wait-Route($routeName, [int]$timeoutMs = 180000) {
  $expr = @"
(async () => {
  const deadline = Date.now() + $timeoutMs;
  while (Date.now() < deadline) {
    if ((window.__HDO_PERF_AUDIT__ || []).some(e => e.kind === "route_fully_rendered" && e.name === "$routeName")) {
      return true;
    }
    await new Promise(r => setTimeout(r, 250));
  }
  return false;
})()
"@
  return Eval-Js $expr ($timeoutMs + 5000)
}

function Click-Path-And-Wait($path, $routeName, [int]$timeoutMs = 180000) {
  $expr = @"
(async () => {
  const before = (window.__HDO_PERF_AUDIT__ || []).length;
  const link = Array.from(document.querySelectorAll("a")).find(a => new URL(a.href).pathname === "$path");
  if (!link) {
    return { clicked: false, path: location.pathname, anchorCount: document.querySelectorAll("a").length };
  }
  link.click();
  const deadline = Date.now() + $timeoutMs;
  while (Date.now() < deadline) {
    const events = window.__HDO_PERF_AUDIT__ || [];
    if (events.slice(before).some(e => e.kind === "route_fully_rendered" && e.name === "$routeName")) {
      return { clicked: true, path: location.pathname, events: events.length };
    }
    await new Promise(r => setTimeout(r, 250));
  }
  return { clicked: true, timeout: true, path: location.pathname, events: (window.__HDO_PERF_AUDIT__ || []).length };
})()
"@
  return Eval-Js $expr ($timeoutMs + 5000)
}

Send-Cdp "Page.enable" | Out-Null
Send-Cdp "Runtime.enable" | Out-Null
Start-Sleep -Seconds 5

$nav = @()
if ($OnlyRoute) {
  $nav += [pscustomobject]@{ route = $OnlyRoute; result = (Wait-Route $OnlyRoute 240000) }
  $eventsJson = Eval-Js "JSON.stringify(window.__HDO_PERF_AUDIT__ || [])" 30000
  $output = @{
    baseUrl = $BaseUrl
    startUrl = $startUrl
    capturedAt = (Get-Date).ToString("o")
    nav = $nav
    events = ($eventsJson | ConvertFrom-Json)
  }
  $output | ConvertTo-Json -Depth 40 | Set-Content -Encoding UTF8 $OutPath
  Write-Output (Resolve-Path $OutPath)
  $ws.Dispose()
  return
}

$nav += [pscustomobject]@{ route = "Home"; result = (Wait-Route "Home" 180000) }
$nav += [pscustomobject]@{ route = "Library"; result = (Click-Path-And-Wait "/library" "Library" 180000) }

$itemExpr = @'
(async () => {
  const before = (window.__HDO_PERF_AUDIT__ || []).length;
  const link = Array.from(document.querySelectorAll("a")).find(a => {
    const p = new URL(a.href).pathname;
    return /^\/library\/.+/.test(p);
  });
  if (!link) {
    return {
      clicked: false,
      reason: "no item link",
      path: location.pathname,
      anchors: Array.from(document.querySelectorAll("a")).map(a => new URL(a.href).pathname).slice(0, 20)
    };
  }
  const target = new URL(link.href).pathname;
  link.click();
  const deadline = Date.now() + 180000;
  while (Date.now() < deadline) {
    const events = window.__HDO_PERF_AUDIT__ || [];
    if (events.slice(before).some(e => e.kind === "route_fully_rendered" && e.name === "Item Detail")) {
      return { clicked: true, target, path: location.pathname, events: events.length };
    }
    await new Promise(r => setTimeout(r, 250));
  }
  return { clicked: true, target, timeout: true, path: location.pathname, events: (window.__HDO_PERF_AUDIT__ || []).length };
})()
'@
$nav += [pscustomobject]@{ route = "Item Detail"; result = (Eval-Js $itemExpr 185000) }
$nav += [pscustomobject]@{ route = "Health"; result = (Click-Path-And-Wait "/health" "Health" 240000) }
$nav += [pscustomobject]@{ route = "Settings"; result = (Click-Path-And-Wait "/settings" "Settings" 180000) }
$nav += [pscustomobject]@{ route = "Recover"; result = (Click-Path-And-Wait "/recover" "Recover" 240000) }

$eventsJson = Eval-Js "JSON.stringify(window.__HDO_PERF_AUDIT__ || [])" 30000
$output = @{
  baseUrl = $BaseUrl
  capturedAt = (Get-Date).ToString("o")
  nav = $nav
  events = ($eventsJson | ConvertFrom-Json)
}
$output | ConvertTo-Json -Depth 40 | Set-Content -Encoding UTF8 $OutPath
Write-Output (Resolve-Path $OutPath)
$ws.Dispose()
