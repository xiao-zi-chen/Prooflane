"""Browser regression for native targets, extra packages and the comparison view.

The Linux upload is explicitly a protocol fixture and is cancelled before any
native Linux execution. It does not count as a Linux application test.
"""
import io
import json
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    output=Path('artifacts')
    output.mkdir(exist_ok=True)
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w') as archive:
        archive.writestr('README.txt','Protocol fixture only. Not a Linux executable. Must not be executed.')
    errors=[]
    campaign=None
    campaign_id=None
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1100},base_url='http://127.0.0.1:8765')
        page.on('pageerror',lambda error: errors.append(str(error)))
        try:
            page.goto('http://127.0.0.1:8765/#new',wait_until='networkidle')
            expect(page.locator('#platform-options .platform-option')).to_have_count(3)
            page.locator('input[name="target-platform"][value="macos"]').check()
            expect(page.locator('#platform-hint')).to_contain_text('实验阶段')
            expect(page.locator('#upload-detail')).to_contain_text('DMG')
            page.locator('input[name="target-platform"][value="windows"]').check()
            page.screenshot(path=str(output/'multiplatform-dashboard.png'),full_page=True)
            page.goto('http://127.0.0.1:8765/#nodes')
            expect(page.locator('.node-card')).to_have_count(3,timeout=10000)
            expect(page.locator('#node-list')).to_contain_text('待对应实机验证')
            page.screenshot(path=str(output/'multiplatform-nodes.png'),full_page=True)
            page.goto('http://127.0.0.1:8765/#new')
            page.locator('#package-file').set_input_files('data/demo/ProoflaneNotes.exe')
            expect(page.locator('#upload-zone')).to_have_class('upload-zone uploaded',timeout=10000)
            page.locator('#run-name').fill('多平台界面回归 · Linux 协议占位包不执行')
            page.locator('#window-title').fill('Prooflane Notes')
            page.locator('.step-editor').nth(1).locator('[data-field="target"]').fill('Save note')
            page.locator('.step-editor').nth(2).locator('[data-field="value"]').fill('Saved:')
            page.locator('#add-platform').click()
            page.locator('[data-extra-field="platform"]').select_option('linux')
            page.locator('[data-extra-upload]').set_input_files({'name':'linux-protocol-fixture.zip','mimeType':'application/zip','buffer':payload.getvalue()})
            expect(page.locator('.extra-upload')).to_contain_text('linux-protocol-fixture.zip',timeout=10000)
            page.locator('#submit-run').click()
            expect(page.locator('.matrix-table')).to_be_visible(timeout=10000)
            campaign_id=page.url.split('#matrix/')[1]
            deadline=time.monotonic()+50
            while time.monotonic()<deadline:
                campaign=page.request.get('/api/campaigns/'+campaign_id).json()
                windows=next(r for r in campaign['runs'] if r['platform']=='windows')
                if windows['status'] in ('passed','failed','interrupted'):
                    break
                page.wait_for_timeout(300)
            assert windows['status']=='passed', windows
            linux=next(r for r in campaign['runs'] if r['platform']=='linux')
            assert linux['status']=='waiting_worker' and not campaign['passed'] and not campaign['complete']
            expect(page.locator('#matrix-content')).to_contain_text('尚未完成')
            expect(page.locator('#matrix-content')).to_contain_text('等待节点')
            page.wait_for_timeout(1900)
            page.screenshot(path=str(output/'multiplatform-matrix.png'),full_page=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(output/'multiplatform-matrix-mobile.png'),full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            (output/'multiplatform-browser-result.json').write_text(json.dumps({'campaign_id':campaign_id,'windows_run_id':windows['id'],
                'windows_status':windows['status'],'linux_status_observed':linux['status'],'linux_executed':False,'javascript_errors':errors},indent=2),encoding='utf-8')
            print('Multi-platform UI passed: selectors, native nodes, per-platform upload, aligned comparison, truthful waiting state, mobile layout.')
        finally:
            if campaign_id and not campaign:
                campaign=page.request.get("/api/campaigns/"+campaign_id).json()
            if campaign:
                for run in campaign['runs']:
                    if run['status'] in ('queued','waiting_worker','preparing','running'):
                        page.request.post(f"/api/runs/{run['id']}/cancel",headers={'X-Prooflane-Client':'web'})
            browser.close()


if __name__=='__main__':
    main()
