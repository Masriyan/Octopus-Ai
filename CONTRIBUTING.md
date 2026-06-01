# 🤝 Contributing to Octopus AI

Thank you for your interest in contributing to **Octopus AI**! 🐙

We welcome contributions of all kinds — bug reports, feature requests, documentation improvements, and code contributions.

---

## 📋 Table of Contents

- [Code of Conduct](#-code-of-conduct)
- [Getting Started](#-getting-started)
- [Development Setup](#-development-setup)
- [How to Contribute](#-how-to-contribute)
- [Pull Request Process](#-pull-request-process)
- [Coding Standards](#-coding-standards)
- [Adding a New Tentacle (Tool)](#-adding-a-new-tentacle-tool)

---

## 📜 Code of Conduct

Be respectful, inclusive, and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/) code of conduct.

---

## 🚀 Getting Started

1. **Fork** the repository on [GitHub](https://github.com/Masriyan/Octopus-Ai)
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/Masriyan/Octopus-Ai.git
   cd Octopus-Ai
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

---

## 🔧 Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment config
cp .env.example .env

# Start the development servers
./start.sh
```

The backend runs on `http://localhost:8000` and the frontend on `http://localhost:5500`.

---

## 💡 How to Contribute

### 🐛 Bug Reports

Open an [issue](https://github.com/Masriyan/Octopus-Ai/issues) with:

- A clear and descriptive title
- Steps to reproduce the bug
- Expected vs. actual behavior
- Your environment (OS, Python version, browser)

### ✨ Feature Requests

Open an [issue](https://github.com/Masriyan/Octopus-Ai/issues) with:

- A clear description of the feature
- Why it would be useful
- Any implementation ideas you have

### 📝 Documentation

Documentation improvements are always welcome! Fix typos, clarify instructions, add examples.

### 🔧 Code Contributions

1. Check existing [issues](https://github.com/Masriyan/Octopus-Ai/issues) for something to work on
2. Comment on the issue to let others know you're working on it
3. Follow the coding standards below
4. Submit a pull request

---

## 🔀 Pull Request Process

1. **Update documentation** if your changes affect the public API or usage
2. **Test your changes** locally — make sure both backend and frontend still work
3. **Write a clear PR description** explaining what and why
4. **Reference related issues** using `Fixes #123` or `Closes #123`
5. **Wait for review** — a maintainer will review and provide feedback

---

## 📐 Coding Standards

### Python (Backend)

- Follow **PEP 8** style guidelines
- Use **type hints** for function signatures
- Write **docstrings** for classes and public functions
- Keep functions focused and under 50 lines when possible
- Use `async/await` for all I/O operations

### JavaScript (Frontend)

- Use **vanilla JS** (no frameworks)
- Keep functions small and descriptive
- Use `const`/`let` — never `var`
- Comment non-obvious logic

### General

- Commit messages should be clear and descriptive
- One logical change per commit
- Keep PRs focused — don't mix unrelated changes

---

## 🦑 Adding a New Tentacle (Tool)

Tools are **class-based** — subclass `BaseTool` and implement `async def execute`.
(See `backend/tools/plan_tool.py` and `delegate_tool.py` for real examples.)

1. Create `backend/tools/your_tool.py`:

   ```python
   from tools import BaseTool

   class YourTool(BaseTool):
       name = "your_tool_name"        # unique; first token is the default permission key
       category = "your_category"     # optional: groups it under a tools_enabled toggle
       description = "What this tool does (the model reads this to decide when to call it)."
       parameters = {
           "type": "object",
           "properties": {
               "param1": {"type": "string", "description": "Description"},
               "param2": {"type": "integer", "description": "Description"},
           },
           "required": ["param1"],
       }

       async def execute(self, param1: str, param2: int = 10, **kwargs) -> dict:
           try:
               result = do_something(param1, param2)
               return {"status": "success", "output": result}
           except Exception as e:
               return {"status": "error", "error": str(e)}
   ```

2. Register it in `backend/tools/__init__.py` — import the class inside
   `register_all_tools()` and add it to the registration list.

3. Add a permission default in `config.py` (`tools_enabled`) and a toggle in
   `frontend/index.html` under **Tentacle Permissions** with id `tool-<category>`.

4. Add an icon in `frontend/js/app.js` — both the inline `toolIcons` map (chat
   tool cards) and the `TOOL_ICONS` map (Agent Activity timeline).

---

## 🙏 Thank You!

Every contribution, no matter how small, makes Octopus AI better. Thank you for being part of this project! 🐙

---

<p align="center">
  <a href="https://github.com/Masriyan/Octopus-Ai">Back to Octopus AI</a>
</p>
