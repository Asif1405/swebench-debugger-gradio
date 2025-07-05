import re, json, shlex, shutil, subprocess, tempfile, textwrap, os
import gradio as gr

from dotenv import load_dotenv
from typing import Dict

load_dotenv()


class TestStatus:
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    PENDING = "PENDING"


def parse_log_calypso(log: str) -> Dict[str,str]:
    test_status_map = {}
    suite = []
    get_test_name = lambda suite, pat, line: " - ".join(
        [" - ".join([x[0] for x in suite]), re.match(pat, line).group(1)]
    ).strip()
    for chunk in log.split(" ./node_modules/.bin/jest ")[1:]:
        for line in chunk.splitlines():
            if line.startswith("Test Suites") or line.startswith("  ● "):
                break
            elif line.strip().startswith("✓"):
                pat = r"^\s+✓\s(.*)\(\d+ms\)$" if re.search(r"\(\d+ms\)", line) else r"^\s+✓\s(.*)"
                test_status_map[get_test_name(suite, pat, line)] = TestStatus.PASSED
            elif line.strip().startswith("✕"):
                pat = r"^\s+✕\s(.*)\(\d+ms\)$" if re.search(r"\(\d+ms\)", line) else r"^\s+✕\s(.*)"
                test_status_map[get_test_name(suite, pat, line)] = TestStatus.FAILED
            elif line and line[0].isspace():
                indent = len(line) - len(line.lstrip())
                if not suite:
                    suite = [(line.strip(), indent)]
                else:
                    while suite and suite[-1][1] >= indent:
                        suite.pop()
                    suite.append((line.strip(), indent))
    return test_status_map

def parse_log_chart_js(log: str) -> Dict[str,str]:
    test_status_map = {}
    for pat, flags in [(r"Chrome\s[\d\.]+\s\(.*?\)\s(.*)FAILED$", re.MULTILINE)]:
        for m in re.findall(pat, log, flags):
            test_status_map[m] = TestStatus.FAILED
    return test_status_map

def parse_log_marked(log: str) -> Dict[str,str]:
    test_status_map = {}
    for line in log.splitlines():
        m = re.match(r"^\d+\)\s(.*)", line)
        if m:
            test_status_map[m.group(1).strip()] = TestStatus.FAILED
    return test_status_map

def parse_log_p5js(log: str) -> Dict[str,str]:
    def remove_json_blocks(log):
        out, in_obj, in_list = [], False, False
        for l in log.splitlines():
            s = l.rstrip()
            if s.endswith("{"): in_obj=True; continue
            if s.endswith("["): in_list=True; continue
            if s in ("}","]"): in_obj=in_list=False; continue
            if in_obj or in_list: continue
            if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
                continue
            out.append(l)
        return "\n".join(out)
    # We just strip JSON blocks and return empty mapping (no statuses)
    _ = remove_json_blocks(log)
    return {}

def parse_log_react_pdf(log: str) -> Dict[str,str]:
    test_status_map = {}
    patterns = [
        (r"^PASS\s(.*)\s\([\d\.]+ms\)", TestStatus.PASSED),
        (r"^FAIL\s(.*)\s\([\d\.]+ms\)", TestStatus.FAILED),
        (r"^PASS\s(.*)", TestStatus.PASSED),
        (r"^FAIL\s(.*)", TestStatus.FAILED),
    ]
    for line in log.splitlines():
        for pat, status in patterns:
            m = re.match(pat, line)
            if m:
                test_status_map[m.group(1).strip()] = status
                break
    return test_status_map

def parse_log_vitest(log: str) -> Dict[str,str]:
    test_status_map = {}
    pat = r"^\s*(✓|×|↓)\s(.+?)(?:\s(\d+\s*m?s?|\[skipped\]))?$"
    for l in log.splitlines():
        m = re.match(pat, l.strip())
        if m:
            sym, name, _ = m.groups()
            if sym=="✓": test_status_map[name]=TestStatus.PASSED
            elif sym=="×": test_status_map[name]=TestStatus.FAILED
            else:        test_status_map[name]=TestStatus.SKIPPED
    return test_status_map

def parse_log_jest(log: str) -> Dict[str,str]:
    test_status_map = {}
    pat = r"^\s*(✓|✕|○)\s(.+?)(?:\s\((\d+\s*m?s)\))?$"
    for l in log.splitlines():
        m = re.match(pat, l.strip())
        if m:
            sym, name, _ = m.groups()
            if sym=="✓": test_status_map[name]=TestStatus.PASSED
            elif sym=="✕":test_status_map[name]=TestStatus.FAILED
            else:         test_status_map[name]=TestStatus.SKIPPED
    return test_status_map

def parse_log_mocha_v2(log: str) -> Dict[str,str]:
    ANSI = re.compile(r"\x1b\[[0-9;]*m")
    PASS = re.compile(r"^\s*[✓√✔]\s+(.*?)(?:\s+\(\d+ms\))?\s*$")
    FAIL = re.compile(r"^\s{4,}\d+\)\s+(.*)")
    CROSS= re.compile(r"^\s*[×✕]\s+(.*)")
    PEND = re.compile(r"^\s*[-•]\s+(.*)")
    SUM  = re.compile(r"^\s*\d+\s+(passing|failing|pending)")
    def strip(x): return ANSI.sub("", x)
    out, stack, empty = {}, [], 0
    for raw in log.splitlines():
        line = strip(raw.rstrip())
        if not line:
            empty+=1
            if empty>=2: stack=[]; empty=0
            continue
        empty=0
        if SUM.match(line):
            stack=[]
            continue
        m = PASS.match(line)
        if m:
            out[" - ".join(stack+[m.group(1).strip()])] = TestStatus.PASSED
            continue
        m = FAIL.match(line) or CROSS.match(line)
        if m:
            out[" - ".join(stack+[m.group(1).strip()])] = TestStatus.FAILED
            continue
        m = PEND.match(line)
        if m:
            out[" - ".join(stack+[m.group(1).strip()])] = TestStatus.PENDING
            continue
        indent = len(line)-len(line.lstrip())
        if indent>=2:
            level = indent//2
            stack[level:]=[line.strip()]
    return out

def parse_log_karma(log: str) -> Dict[str,str]:
    out, suite, started = {}, [], False
    pat = re.compile(r"^(\s*)?([✔✖])?\s(.*)$")
    for l in log.splitlines():
        if l.startswith("SUMMARY:"): return out
        if "Starting browser" in l:
            started=True
            continue
        if not started: continue
        m = pat.match(l)
        if not m: continue
        indent, sym, name = m.groups()
        if indent and not sym:
            lvl = len(indent)
            if lvl> (len(suite)-1)*2:
                suite.append(name)
            else:
                suite.pop()
        elif sym in ("✔","✖"):
            full = " > ".join(suite+[name])
            out[full] = TestStatus.PASSED if sym=="✔" else TestStatus.FAILED
    return out

def parse_log_tap(log: str) -> Dict[str,str]:
    out = {}
    pat = re.compile(r"^(ok|not ok) (\d+) (.+)$")
    for l in log.splitlines():
        m = pat.match(l.strip())
        if m:
            status,name = (TestStatus.PASSED, m.group(3)) if m.group(1)=="ok" else (TestStatus.FAILED, m.group(3))
            out[name] = status
    return out

def get_js_parser_by_name(name: str):
    return {
        "calypso":  parse_log_calypso,
        "chartjs":  parse_log_chart_js,
        "marked":   parse_log_marked,
        "p5js":     parse_log_p5js,
        "reactpdf": parse_log_react_pdf,
        "vitest":   parse_log_vitest,
        "jest":     parse_log_jest,
        "mocha":    parse_log_mocha_v2,
        "karma":    parse_log_karma,
        "tap":      parse_log_tap,
    }.get(name, parse_log_vitest)


def build_image(specs_json: str,
                repo_url: str,
                base_commit: str,
                head_commit: str,
                commit_choice: str,
                docker_path: str):
    """
    Generator: builds 'test-image' and yields the full accumulated log.
    """
    accum = ""

    # 1) Parse JSON
    try:
        specs = json.loads(specs_json)
    except json.JSONDecodeError as e:
        yield f"❌ Invalid JSON:\n{e}\n"
        return

    node_ver = specs.get("docker_specs", {}).get("node_version")
    if not node_ver:
        yield "❌ JSON must include docker_specs.node_version\n"
        return

    # 2) Prepare docker command list, handle sudo fallback
    parts = shlex.split(docker_path)
    if not parts:
        accum += "❌ Docker executable command is empty.\n"
        yield accum
        return
    # If first token is 'sudo' but sudo is missing, strip it
    if parts[0] == "sudo" and shutil.which("sudo") is None:
        if len(parts) > 1 and shutil.which(parts[1]):
            accum += f"⚠ 'sudo' not found; stripping prefix and using '{parts[1]}' instead.\n"
            parts = parts[1:]
        else:
            accum += "❌ Neither 'sudo' nor fallback command found.\n"
            yield accum
            return
    # If primary command missing
    if shutil.which(parts[0]) is None:
        accum += f"❌ Command '{parts[0]}' not found in PATH.\n"
        yield accum
        return
    docker_cmd = parts

    # 3) Start build
    accum += "🔨 Starting Docker build...\n"
    yield accum

    # 4) Create workspace + write Dockerfile
    work_dir = tempfile.mkdtemp(prefix="js-docker-")
    try:
        df_tpl = textwrap.dedent("""\
            FROM --platform=linux/amd64 ubuntu:22.04
            ARG DEBIAN_FRONTEND=noninteractive
            ENV TZ=Etc/UTC

            RUN apt-get update && apt-get install -y \\
                build-essential curl git libssl-dev software-properties-common \\
                wget gnupg jq ca-certificates dbus ffmpeg imagemagick \\
                libcairo2-dev libpango1.0-dev libjpeg-dev libgif-dev \\
                librsvg2-dev pkg-config && rm -rf /var/lib/apt/lists/*

            RUN bash -c "set -eo pipefail && curl -fsSL https://deb.nodesource.com/setup_{node_version}.x | bash -"
            RUN apt-get update && apt-get install -y nodejs && rm -rf /var/lib/apt/lists/*

            RUN node -v && npm -v

            RUN npm install -g corepack@latest && corepack enable pnpm
            RUN npm install -g pnpm@latest --force

            RUN apt-get update && apt-get install -y chromium-browser && rm -rf /var/lib/apt/lists/*
            ENV CHROME_BIN=/usr/bin/chromium-browser
            ENV CHROME_PATH=/usr/bin/chromium-browser

            RUN adduser --disabled-password --gecos 'dog' nonroot

            COPY ./setup_env.sh /root/
            RUN sed -i -e 's/\\r$//' /root/setup_env.sh && \\
                chmod +x /root/setup_env.sh && \\
                /bin/bash -lc "source /root/setup_env.sh"

            RUN apt-get update && apt-get install -y python3 python3-pip python2 && \\
                ln -sf /usr/bin/python3 /usr/bin/python && rm -rf /var/lib/apt/lists/*

            RUN python -V && python3 -V && python2 -V

            WORKDIR /testbed/

            COPY ./setup_repo.sh /root/
            RUN sed -i -e 's/\\r$//' /root/setup_repo.sh && \\
                chmod +x /root/setup_repo.sh && \\
                /bin/bash /root/setup_repo.sh

            WORKDIR /testbed/
        """)
        dockerfile_path = os.path.join(work_dir, "Dockerfile")
        with open(dockerfile_path, "w") as df:
            df.write(df_tpl.replace("{node_version}", node_ver))

        # Stub setup_env.sh
        env_sh = os.path.join(work_dir, "setup_env.sh")
        with open(env_sh, "w") as f:
            f.write("#!/bin/bash\nset -euxo pipefail\n# no-op stub\n")
        os.chmod(env_sh, 0o755)

        # Generate setup_repo.sh
        cmds = [
            "#!/bin/bash", "set -euxo pipefail",
            f"git clone -o origin {repo_url} /testbed",
            "chmod -R 777 /testbed", "cd /testbed",
            f"git reset --hard {base_commit}"
        ]
        if commit_choice == "head":
            cmds += ["git fetch origin", f"git checkout {head_commit}"]
        for phase in ("pre_install", "install", "build"):
            cmds += specs.get(phase, [])
        repo_sh = os.path.join(work_dir, "setup_repo.sh")
        with open(repo_sh, "w") as sr:
            sr.write("\n".join(cmds) + "\n")
        os.chmod(repo_sh, 0o755)

        # Stream docker build
        proc = subprocess.Popen(
            docker_cmd + ["build", "-t", "test-image", "."],
            cwd=work_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in proc.stdout:
            accum += line
            yield accum
        proc.stdout.close()
        code = proc.wait()
        accum += f"\n✅ Build finished with exit code {code}.\n"
        yield accum

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def run_tests(specs_json: str,
              docker_path: str,
              test_files_str: str):
    """
    Generator: runs tests in 'test-image', yielding accumulated logs.
    """
    accum = ""

    # Prepare docker cmd
    parts = shlex.split(docker_path)
    if parts and parts[0] == "sudo" and shutil.which("sudo") is None and len(parts)>1 and shutil.which(parts[1]):
        accum += f"⚠ 'sudo' not found; stripping to '{parts[1]}'.\n"
        parts = parts[1:]
    if not parts or shutil.which(parts[0]) is None:
        accum += f"❌ Command '{parts[0] if parts else ''}' not found.\n"
        yield accum
        return
    docker_cmd = parts

    # Parse JSON
    try:
        specs = json.loads(specs_json)
    except json.JSONDecodeError as e:
        yield f"❌ Invalid JSON:\n{e}\n"
        return

    # Check image
    img = subprocess.run(
        docker_cmd + ["images", "-q", "test-image"],
        stdout=subprocess.PIPE, text=True
    ).stdout.strip()
    if not img:
        yield "❌ No 'test-image' found. Build first.\n"
        return

    test_cmd = specs.get("test_cmd", "").strip()
    if not test_cmd:
        yield "❌ JSON must include test_cmd\n"
        return

    files = test_files_str.strip().split()
    cmd = f"cd /testbed && {test_cmd} {' '.join(files)}"
    accum += "🧪 Running tests...\n"
    yield accum

    proc = subprocess.Popen(
        docker_cmd + ["run", "--rm", "test-image", "bash", "-lc", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    for line in proc.stdout:
        accum += line
        yield accum
    proc.stdout.close()
    code = proc.wait()
    accum += f"\n✅ Tests finished with exit code {code}.\n"
    yield accum


with gr.Blocks() as demo:
    gr.Markdown("## JS Docker Build & Test Runner")

    with gr.Row():
        specs      = gr.Textbox(label="Repo Specs JSON", lines=6)
        docker_path= gr.Textbox(label="Docker executable command", value="docker")

    with gr.Row():
        repo_url   = gr.Textbox(label="Git Repo URL")
        base_sha   = gr.Textbox(label="Base Commit SHA")
        head_sha   = gr.Textbox(label="Head Commit SHA")
        commit_sel = gr.Radio(["base","head"], label="Commit to build", value="head")

    with gr.Row():
        btn_build = gr.Button("🔨 Build Image")
        btn_test  = gr.Button("🧪 Run Tests")
        parser    = gr.Dropdown(
            choices=["calypso","chartjs","marked","p5js","reactpdf",
                     "vitest","jest","mocha","karma","tap"],
            label="Log Parser"
        )
        raw_log   = gr.Textbox(label="Raw Log to Parse", lines=6, placeholder="Paste build/test logs…")
        btn_parse = gr.Button("🔍 Parse Logs")

    output = gr.Textbox(label="Logs / Parsed Output", lines=20)

    btn_build.click(
        fn=build_image,
        inputs=[specs, repo_url, base_sha, head_sha, commit_sel, docker_path],
        outputs=output
    )
    btn_test.click(
        fn=run_tests,
        inputs=[specs, docker_path, raw_log],  # reuse raw_log for tests paths
        outputs=output
    )
    btn_parse.click(
        fn=lambda name, log: json.dumps(get_js_parser_by_name(name)(log), indent=2),
        inputs=[parser, raw_log],
        outputs=output
    )

if __name__ == "__main__":
    port = int(os.getenv("GRADIO_SERVER_PORT", 7860))
    demo.queue().launch(server_name="0.0.0.0", server_port=port)
