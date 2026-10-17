from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Step(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=150)
    action: Literal["wait_window", "click", "type_text", "assert_text", "screenshot"]
    target: str = Field(default="", max_length=250)
    automation_id: str = Field(default="", max_length=250)
    control_type: str = Field(default="", max_length=40)
    value: str = Field(default="", max_length=2000)
    timeout: int = Field(default=15, ge=2, le=60)

    @model_validator(mode="after")
    def check_target(self):
        if self.action in ("click", "type_text") and not (self.target.strip() or self.automation_id.strip()):
            raise ValueError("点击和输入需要控件名称或 Automation ID")
        if self.action == "assert_text" and not self.value.strip():
            raise ValueError("文本检查需要填写预期文本")
        return self


class RunSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    platform: Literal["windows", "macos", "linux"] = "windows"
    architecture: Literal["any", "x86_64", "arm64"] = "any"
    package_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    mode: Literal["portable", "installer"] = "portable"
    app_path: str = Field(default="", max_length=500)
    install_args: list[str] = Field(default_factory=list, max_length=30)
    app_args: list[str] = Field(default_factory=list, max_length=30)
    window_title: str = Field(min_length=1, max_length=250)
    steps: list[Step] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def check_launch(self):
        if self.mode == "installer" and not self.app_path.strip():
            raise ValueError("安装模式需要填写安装后的程序完整路径")
        if self.platform == "windows" and self.mode == "installer" and not self.install_args:
            raise ValueError("请填写安装包的静默安装参数；MSI 可填写 /qn /norestart")
        if any(len(arg) > 2000 or "\x00" in arg for arg in self.install_args + self.app_args):
            raise ValueError("启动参数无效")
        return self


class CampaignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    targets: list[RunSpec] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def aligned_steps(self):
        keys = [(t.platform, t.architecture) for t in self.targets]
        if len(set(keys)) != len(keys):
            raise ValueError("同一平台与架构不能重复")
        shape = [(s.title, s.action) for s in self.targets[0].steps]
        if any([(s.title, s.action) for s in t.steps] != shape for t in self.targets[1:]):
            raise ValueError("跨平台对照必须共享步骤名称与操作类型；控件定位和预期文本可按平台调整")
        return self


class NodeRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    platform: Literal["windows", "macos", "linux"]
    architecture: Literal["x86_64", "arm64"]
    ready: bool = False
    detail: str = Field(default="", max_length=1000)


class LeaseProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lease: str = Field(min_length=20, max_length=100)
    status: Literal["preparing", "installing", "running"]
    steps: list[dict] = Field(default_factory=list, max_length=5)
    environment: dict = Field(default_factory=dict)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    step_index: int = Field(ge=0, le=4)
    decision: Literal["passed", "failed"]
    note: str = Field(min_length=1, max_length=1000)


DEMO_STEPS = [
    {"title": "启动应用，确认主窗口出现", "action": "wait_window"},
    {"title": "输入一条待保存的笔记", "action": "type_text", "automation_id": "noteInput", "value": "Hello from Prooflane"},
    {"title": "点击保存", "action": "click", "automation_id": "saveButton"},
    {"title": "检查保存成功提示", "action": "assert_text", "value": "Saved: Hello from Prooflane"},
    {"title": "截取界面，等待人工复核布局", "action": "screenshot"},
]
