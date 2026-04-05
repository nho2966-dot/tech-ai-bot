1s
Current runner version: '2.333.1'
Runner Image Provisioner
Operating System
Runner Image
GITHUB_TOKEN Permissions
Secret source: Actions
Prepare workflow directory
Prepare all required actions
Getting action download info
Download action repository 'actions/checkout@v4' (SHA:34e114876b0b11c390a56381ad16ebd13914f8d5)
Download action repository 'actions/setup-python@v5' (SHA:a26af69be951a213d495a4c3e4e4022e16d87065)
Download action repository 'actions/download-artifact@v4' (SHA:d3f86a106a0bac45b974a628896c90dbdf5c8093)
Download action repository 'actions/upload-artifact@v4' (SHA:ea165f8d65b6e75b540449e92b4886f43607fa02)
Complete job name: run-bot
1s
Run actions/checkout@v4
Syncing repository: nho2966-dot/tech-ai-bot
Getting Git version info
Temporarily overriding HOME='/home/runner/work/_temp/067e5fa1-bf99-419a-a5cd-4ae716a8431c' before making global git config changes
Adding repository directory to the temporary git global config as a safe directory
/usr/bin/git config --global --add safe.directory /home/runner/work/tech-ai-bot/tech-ai-bot
Deleting the contents of '/home/runner/work/tech-ai-bot/tech-ai-bot'
Initializing the repository
Disabling automatic garbage collection
Setting up auth
Fetching the repository
Determining the checkout info
/usr/bin/git sparse-checkout disable
/usr/bin/git config --local --unset-all extensions.worktreeConfig
Checking out the ref
/usr/bin/git log -1 --format=%H
2110836a400467cd6eb1b4f4901d803309a6db6f
2s
Run actions/setup-python@v5
Installed versions
/opt/hostedtoolcache/Python/3.10.20/x64/bin/pip cache dir
/home/runner/.cache/pip
Received 58384973 of 58384973 (100.0%), 83.7 MBs/sec
Cache Size: ~56 MB (58384973 B)
/usr/bin/tar -xf /home/runner/work/_temp/6a1eb778-2cd4-44ae-935d-3edabcb7c233/cache.tzst -P -C /home/runner/work/tech-ai-bot/tech-ai-bot --use-compress-program unzstd
Cache restored successfully
Cache restored from key: setup-python-Linux-x64-24.04-Ubuntu-python-3.10.20-pip-f8d72b779a528058af651eefde9e282c910a64e27019678a85f326208801724f
3s
Run python -m pip install --upgrade pip
  
Requirement already satisfied: pip in /opt/hostedtoolcache/Python/3.10.20/x64/lib/python3.10/site-packages (26.0.1)
Collecting tweepy
  Using cached tweepy-4.16.0-py3-none-any.whl.metadata (3.3 kB)
Collecting httpx
  Using cached httpx-0.28.1-py3-none-any.whl.metadata (7.1 kB)
Collecting loguru
  Using cached loguru-0.7.3-py3-none-any.whl.metadata (22 kB)
Collecting python-dotenv
  Using cached python_dotenv-1.2.2-py3-none-any.whl.metadata (27 kB)
Collecting apscheduler
  Using cached apscheduler-3.11.2-py3-none-any.whl.metadata (6.4 kB)
Collecting oauthlib<4,>=3.2.0 (from tweepy)
  Using cached oauthlib-3.3.1-py3-none-any.whl.metadata (7.9 kB)
Collecting requests<3,>=2.27.0 (from tweepy)
  Downloading requests-2.33.1-py3-none-any.whl.metadata (4.8 kB)
Collecting requests-oauthlib<3,>=1.2.0 (from tweepy)
  Using cached requests_oauthlib-2.0.0-py2.py3-none-any.whl.metadata (11 kB)
Collecting charset_normalizer<4,>=2 (from requests<3,>=2.27.0->tweepy)
  Downloading charset_normalizer-3.4.7-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (40 kB)
Collecting idna<4,>=2.5 (from requests<3,>=2.27.0->tweepy)
  Using cached idna-3.11-py3-none-any.whl.metadata (8.4 kB)
Collecting urllib3<3,>=1.26 (from requests<3,>=2.27.0->tweepy)
  Using cached urllib3-2.6.3-py3-none-any.whl.metadata (6.9 kB)
Collecting certifi>=2023.5.7 (from requests<3,>=2.27.0->tweepy)
  Using cached certifi-2026.2.25-py3-none-any.whl.metadata (2.5 kB)
Collecting anyio (from httpx)
  Downloading anyio-4.13.0-py3-none-any.whl.metadata (4.5 kB)
Collecting httpcore==1.* (from httpx)
  Using cached httpcore-1.0.9-py3-none-any.whl.metadata (21 kB)
Collecting h11>=0.16 (from httpcore==1.*->httpx)
  Using cached h11-0.16.0-py3-none-any.whl.metadata (8.3 kB)
Collecting tzlocal>=3.0 (from apscheduler)
  Using cached tzlocal-5.3.1-py3-none-any.whl.metadata (7.6 kB)
Collecting exceptiongroup>=1.0.2 (from anyio->httpx)
  Using cached exceptiongroup-1.3.1-py3-none-any.whl.metadata (6.7 kB)
Collecting typing_extensions>=4.5 (from anyio->httpx)
  Using cached typing_extensions-4.15.0-py3-none-any.whl.metadata (3.3 kB)
Using cached tweepy-4.16.0-py3-none-any.whl (98 kB)
Using cached oauthlib-3.3.1-py3-none-any.whl (160 kB)
Downloading requests-2.33.1-py3-none-any.whl (64 kB)
Downloading charset_normalizer-3.4.7-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (216 kB)
Using cached idna-3.11-py3-none-any.whl (71 kB)
Using cached requests_oauthlib-2.0.0-py2.py3-none-any.whl (24 kB)
Using cached urllib3-2.6.3-py3-none-any.whl (131 kB)
Using cached httpx-0.28.1-py3-none-any.whl (73 kB)
Using cached httpcore-1.0.9-py3-none-any.whl (78 kB)
Using cached loguru-0.7.3-py3-none-any.whl (61 kB)
Using cached python_dotenv-1.2.2-py3-none-any.whl (22 kB)
Using cached apscheduler-3.11.2-py3-none-any.whl (64 kB)
Using cached certifi-2026.2.25-py3-none-any.whl (153 kB)
Using cached h11-0.16.0-py3-none-any.whl (37 kB)
Using cached tzlocal-5.3.1-py3-none-any.whl (18 kB)
Downloading anyio-4.13.0-py3-none-any.whl (114 kB)
Using cached exceptiongroup-1.3.1-py3-none-any.whl (16 kB)
Using cached typing_extensions-4.15.0-py3-none-any.whl (44 kB)
Installing collected packages: urllib3, tzlocal, typing_extensions, python-dotenv, oauthlib, loguru, idna, h11, charset_normalizer, certifi, requests, httpcore, exceptiongroup, apscheduler, requests-oauthlib, anyio, tweepy, httpx
Successfully installed anyio-4.13.0 apscheduler-3.11.2 certifi-2026.2.25 charset_normalizer-3.4.7 exceptiongroup-1.3.1 h11-0.16.0 httpcore-1.0.9 httpx-0.28.1 idna-3.11 loguru-0.7.3 oauthlib-3.3.1 python-dotenv-1.2.2 requests-2.33.1 requests-oauthlib-2.0.0 tweepy-4.16.0 typing_extensions-4.15.0 tzlocal-5.3.1 urllib3-2.6.3
0s
Run actions/download-artifact@v4
  
Downloading single artifact
Error: Unable to download artifact(s): Artifact not found for name: tech-database
        Please ensure that your artifact is not expired and the artifact was uploaded using a compatible version of toolkit/upload-artifact.
        For more information, visit the GitHub Artifacts FAQ: https://github.com/actions/toolkit/blob/main/packages/artifact/docs/faq.md
4s
Run python main.py manual
  
2026-04-05 09:29:09.640 | INFO     | __main__:main_loop:220 - 🚀 Sniper Engine Online | Mode: manual
2026-04-05 09:29:09.640 | INFO     | __main__:run_mission:170 - 📡 بدء مهمة النشر الذاتي (Independent Mode)...
2026-04-05 09:29:11.696 | ERROR    | __main__:run_mission:200 - Mission Error: 402 Payment Required
Your enrolled account [2005187138799951872] does not have any credits to fulfill this request.
2026-04-05 09:29:11.696 | INFO     | __main__:smart_reply:121 - 🕵️ فحص المنشنات للردود الذكية...
2026-04-05 09:29:11.847 | ERROR    | __main__:smart_reply:166 - Reply Error: 402 Payment Required
Your enrolled account [2005187138799951872] does not have any credits to fulfill this request.
2026-04-05 09:29:11.847 | INFO     | __main__:update_stats:204 - 📊 تحديث إحصائيات الأداء...
1s
Run actions/upload-artifact@v4
  
With the provided path, there will be 1 file uploaded
Artifact name is valid!
Root directory input is valid!
Beginning upload of artifact content to blob storage
Uploaded bytes 438
Finished uploading artifact content to blob storage!
SHA256 digest of uploaded artifact zip is fc6e1fec5cd2842150bc815cf5ba4e56c147710882f9254f6c69ec7e4e462f62
Finalizing artifact upload
Artifact tech-database.zip successfully finalized. Artifact ID 6276475111
Artifact tech-database has been successfully uploaded! Final size is 438 bytes. Artifact ID is 6276475111
Artifact download URL: https://github.com/nho2966-dot/tech-ai-bot/actions/runs/23998712791/artifacts/6276475111
0s
Post job cleanup.
Cache hit occurred on the primary key setup-python-Linux-x64-24.04-Ubuntu-python-3.10.20-pip-f8d72b779a528058af651eefde9e282c910a64e27019678a85f326208801724f, not saving cache.
0s
Post job cleanup.
/usr/bin/git version
git version 2.53.0
Temporarily overriding HOME='/home/runner/work/_temp/a924cbd0-09ae-44a0-8a8a-f0848c18a1e1' before making global git config changes
Adding repository directory to the temporary git global config as a safe directory
/usr/bin/git config --global --add safe.directory /home/runner/work/tech-ai-bot/tech-ai-bot
/usr/bin/git config --local --name-only --get-regexp core\.sshCommand
/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'core\.sshCommand' && git config --local --unset-all 'core.sshCommand' || :"
/usr/bin/git config --local --name-only --get-regexp http\.https\:\/\/github\.com\/\.extraheader
http.https://github.com/.extraheader
/usr/bin/git config --local --unset-all http.https://github.com/.extraheader
/usr/bin/git submodule foreach --recursive sh -c "git config --local --name-only --get-regexp 'http\.https\:\/\/github\.com\/\.extraheader' && git config --local --unset-all 'http.https://github.com/.extraheader' || :"
/usr/bin/git config --local --name-only --get-regexp ^includeIf\.gitdir:
/usr/bin/git submodule foreach --recursive git config --local --show-origin --name-only --get-regexp remote.origin.url
