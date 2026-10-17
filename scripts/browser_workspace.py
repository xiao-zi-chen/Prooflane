"""Exercise real Windows evidence in a three-target campaign. Never mock OS results."""
import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main(keep_demo=False, existing_campaign=None):
    output = Path("artifacts")
    output.mkdir(exist_ok=True)
    errors, failed_requests = [], []
    campaign_id = None
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100},
            base_url="http://127.0.0.1:8765", permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: failed_requests.append(response.url) if response.status >= 400 else None)
        try:
            page.goto("/", wait_until="networkidle")
            expect(page.locator("#view-overview")).to_be_visible()
            expect(page.locator("#platform-readiness .readiness-platforms>a")).to_have_count(3)
            if existing_campaign:
                page.goto('/#matrix/'+existing_campaign)
            else:
                page.locator("#campaign-demo").click()
            expect(page.locator("#view-matrix .comparison-card")).to_have_count(3, timeout=15000)
            campaign_id = page.url.split("#matrix/")[1]
            deadline = time.monotonic() + 75
            while time.monotonic() < deadline:
                campaign = page.request.get("/api/campaigns/" + campaign_id).json()
                windows = next(r for r in campaign["runs"] if r["platform"] == "windows")
                if windows["status"] in ("passed", "failed", "interrupted"):
                    break
                page.wait_for_timeout(300)
            assert windows["status"] == "passed", windows.get("error")
            for run in campaign["runs"]:
                if run["platform"] != "windows":
                    assert run["status"] == "waiting_worker", run
                    assert not run["artifacts"]
            assert not campaign["complete"] and not campaign["passed"]
            panel = page.locator("#view-matrix")
            expect(panel.locator('[data-platform="windows"] .compare-image img')).to_be_visible(timeout=10000)
            for index in range(4):
                panel.locator(f'[data-compare-step="{index}"]').click()
                shot = panel.locator('[data-platform="windows"] .compare-image img')
                expect(shot).to_have_attribute("src", f"/api/runs/{windows['id']}/artifacts/step-{index+1:02}.png")
                assert shot.evaluate("img=>img.complete && img.naturalWidth>0")
                expect(panel.locator('[data-platform="macos"] img')).to_have_count(0)
                expect(panel.locator('[data-platform="linux"] img')).to_have_count(0)
            panel.locator('.compare-image').click()
            expect(page.locator('#image-dialog')).to_be_visible()
            expect(page.locator('#image-caption')).to_contain_text('Windows')
            page.locator('#close-image').click()
            panel.locator('[data-compare-media="video"]').click()
            video = panel.locator('video')
            expect(video).to_have_count(1)
            video.evaluate("async v=>{window.prooflaneVideo=v;v.muted=true;await v.play()}")
            page.wait_for_timeout(2200)
            assert video.evaluate("v=>v===window.prooflaneVideo && v.currentTime>0"), "Polling replaced the video"
            panel.locator('[data-compare-media="image"]').click()
            page.locator('#copy-matrix').click()
            copied = page.evaluate('navigator.clipboard.readText()')
            assert all(kind in copied for kind in ('Windows', 'macOS', 'Linux', 'waiting_worker'))
            page.screenshot(path=str(output/'workspace-matrix.png'), full_page=True)
            page.goto('/#overview')
            expect(page.locator('#workspace-evidence [data-platform="windows"] img')).to_have_attribute(
                'src', f"/api/runs/{windows['id']}/artifacts/step-04.png", timeout=10000)
            expect(page.locator('#toast')).to_be_hidden(timeout=5000)
            page.screenshot(path=str(output/'workspace-desktop.png'), full_page=True)
            page.goto('/#nodes/macos')
            expect(page.locator('#node-setup')).to_contain_text('requirements-macos.txt')
            page.goto('/#nodes/linux')
            expect(page.locator('#node-setup')).to_contain_text('gir1.2-gtk-3.0')
            page.locator('[data-copy-node]').click()
            assert 'linux-node' in page.evaluate('navigator.clipboard.readText()')
            page.screenshot(path=str(output/'workspace-node-setup.png'), full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            for route in ('overview', 'matrix/'+campaign_id, 'nodes/macos', 'new'):
                page.goto('/#'+route)
                page.wait_for_timeout(2000)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), route
                if route == 'overview':
                    expect(page.locator('#toast')).to_be_hidden(timeout=5000)
                    page.screenshot(path=str(output/'workspace-mobile.png'), full_page=True)
            assert not errors, errors
            assert not failed_requests, failed_requests
            (output/'workspace-result.json').write_text(json.dumps({
                'campaign_id':campaign_id,'windows_run_id':windows['id'],'windows_status':windows['status'],
                'macos_status':'waiting_worker','linux_status':'waiting_worker',
                'macos_executed':False,'linux_executed':False,'javascript_errors':errors,
                'checks':['default workspace','three native packages','same-step screenshot provenance','image zoom',
                          'video playback survives polling','feedback copy','platform setup','mobile layout'],
                'kept_for_user':keep_demo},ensure_ascii=False,indent=2),encoding='utf-8')
            print('Workspace browser checks passed; Windows executed, macOS/Linux truthfully waiting.')
        finally:
            if campaign_id and not keep_demo:
                campaign = page.request.get('/api/campaigns/'+campaign_id).json()
                for run in campaign['runs']:
                    if run['status'] in ('queued','waiting_worker','preparing','running'):
                        page.request.post(f"/api/runs/{run['id']}/cancel",headers={'X-Prooflane-Client':'web'})
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--keep-demo', action='store_true', help='Keep waiting native tasks for the operator to connect nodes')
    parser.add_argument('--existing-campaign', help='Recheck an existing campaign without submitting more native runs')
    args = parser.parse_args()
    main(args.keep_demo, args.existing_campaign)
