"""UI smoke checks against a running local server; screenshots stay local."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright, expect


def main():
    output = Path("artifacts")
    output.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8765/#new", wait_until="networkidle")
        page.get_by_role("heading", name="发起测试").wait_for()
        assert page.locator(".step-editor").count() == 3
        page.get_by_role("button", name="添加验收步骤").click()
        assert page.locator(".step-editor").count() == 4
        page.get_by_role("button", name="删除第 4 步").click()
        page.evaluate("window.scrollTo(0,0)")
        print("Body font:", page.evaluate("getComputedStyle(document.body).fontFamily"))
        page.screenshot(path=str(output / "dashboard-desktop.png"), full_page=True)
        page.get_by_role("link", name="运行记录").click()
        page.get_by_role("heading", name="运行记录", exact=True).wait_for()
        page.wait_for_timeout(700)
        rows = page.locator("tr[data-run]")
        if rows.count():
            rows.first.click()
            page.get_by_role("heading", name="验收步骤", exact=True).wait_for()
            page.screenshot(path=str(output / "report-desktop.png"), full_page=True)
        page.goto("http://127.0.0.1:8765/#guide")
        page.get_by_role("heading", name="使用说明").wait_for()
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto("http://127.0.0.1:8765/#new")
        page.get_by_role("heading", name="发起测试").wait_for()
        page.screenshot(path=str(output / "dashboard-mobile.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "Mobile layout overflows"
        page.set_viewport_size({"width": 1440, "height": 1100})
        fixture = Path("data/demo/ProoflaneNotes.exe")
        if fixture.exists():
            page.locator("#package-file").set_input_files(fixture)
            expect(page.locator("#upload-zone")).to_have_class("upload-zone uploaded", timeout=10000)
            page.locator("#run-name").fill("浏览器回归 · 表单提交与证据下载")
            page.locator("#window-title").fill("Prooflane Notes")
            page.locator('.step-editor').nth(1).locator('[data-field="target"]').fill("Save note")
            page.locator('.step-editor').nth(2).locator('[data-field="value"]').fill("Saved:")
            page.locator("#submit-run").click()
            expect(page.get_by_role("link", name="下载报告包")).to_be_visible(timeout=90000)
            expect(page.locator(".summary-cell").first).to_contain_text("通过")
            page.locator("video").evaluate("async video => { video.muted = true; await video.play(); }")
            for _ in range(75):
                if page.locator("video").evaluate("video => video.currentTime") > 0.1:
                    break
                page.wait_for_timeout(200)
            else:
                raise AssertionError("Recorded MP4 did not play in the browser")
            page.locator("video").evaluate("video => video.pause()")
            page.locator(".step-screenshot").first.click()
            expect(page.locator("#image-dialog")).to_be_visible()
            page.locator("#close-image").click()
            with page.expect_download() as pending:
                page.get_by_role("link", name="下载报告包").click()
            download = pending.value
            download.save_as(str(output / "browser-report.zip"))
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path=str(output / "browser-submitted-report.png"), full_page=True)
            (output / "browser-result.json").write_text(json.dumps({"url": page.url, "status": "passed"}), encoding="utf-8")
        assert not errors, errors
        browser.close()
    print("Browser checks passed: desktop, mobile, step editing, history, report, guide; no JS errors.")


if __name__ == "__main__":
    main()
