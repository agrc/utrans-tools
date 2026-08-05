param(
  [Parameter(Mandatory = $true)]
  [string]$ConfigPath
)

$content = [System.IO.File]::ReadAllText($ConfigPath)
$pattern = '(<AddInInfo\b[^>]*\bversion\s*=\s*")(\d+)\.(\d+)(")'
$match = [System.Text.RegularExpressions.Regex]::Match($content, $pattern)

if (-not $match.Success) {
  throw "Could not find an AddInInfo version in '$ConfigPath'. Expected a major.minor version."
}

$nextVersion = '{0}.{1}' -f $match.Groups[2].Value, ([int]$match.Groups[3].Value + 1)
$replaceVersion = [System.Text.RegularExpressions.MatchEvaluator]{
  param($versionMatch)
  $versionMatch.Groups[1].Value + $nextVersion + $versionMatch.Groups[4].Value
}
$updatedContent = [System.Text.RegularExpressions.Regex]::Replace(
  $content,
  $pattern,
  $replaceVersion,
  1)

[System.IO.File]::WriteAllText(
  $ConfigPath,
  $updatedContent,
  [System.Text.UTF8Encoding]::new($false))

Write-Host "Updated AddInInfo version to $nextVersion."
