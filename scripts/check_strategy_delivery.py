"""Check the handoff UI and run its exported Windows kit outside this project."""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:8765"
ROOT = Path(__file__).resolve().parent.parent


def main():
    output = ROOT / "artifacts"
    with httpx.Client(base_url=BASE, timeout=30) as client:
        health = client.get('/api/health').json()
        assert health['active_run'] is None and health['queue_size'] == 0, 'Wait until the desktop is idle'
        runs = client.get('/api/runs').json()
        source = next(run for run in runs if run['platform']=='windows' and run['status']=='passed'
                      and run['package'].get('demo') and len(run['steps'])==4)
        source_before = client.get('/api/runs/'+source['id']).json()
        response = client.get('/api/strategies/windows/kit',params={'run_id':source['id'],'include_package':True})
        response.raise_for_status()
        with tempfile.TemporaryDirectory(prefix='prooflane-handoff-') as temp:
            kit = Path(temp)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                archive.extractall(kit)
            manifest = json.loads((kit/'scenario.json').read_text(encoding='utf-8'))
            env = dict(os.environ, PYTHONIOENCODING='utf-8')
            env.pop('PYTHONPATH',None)
            command = [sys.executable,'-m','prooflane.handoff','--manifest','scenario.json',
                       '--package',manifest['package']['file']]
            check = subprocess.run(command+['--check'],cwd=kit,env=env,capture_output=True,encoding='utf-8',timeout=30)
            assert check.returncode==0, check.stdout+check.stderr
            assert not (kit/'results').exists(), 'Preflight unexpectedly created execution data'
            result = subprocess.run(command,cwd=kit,env=env,capture_output=True,encoding='utf-8',timeout=100)
            assert result.returncode==0, result.stdout+result.stderr
            receipt_file = next((kit/'results').glob('*/receipt.json'))
            receipt = json.loads(receipt_file.read_text(encoding='utf-8'))
            assert receipt['source_run_id']==source['id'] and receipt['execution_status']=='passed'
            assert receipt['review_status']=='pending'
            with zipfile.ZipFile(receipt_file.parent/'evidence.zip') as evidence:
                report = json.loads(evidence.read('report.json'))
                assert report['platform']=='windows'
                assert report['package']['sha256']==source['package']['sha256']
                assert len(report['steps'])==4 and all(s['status']=='passed' for s in report['steps'])
                assert all(s['screenshot'] in evidence.namelist() for s in report['steps'])
                assert 'recording.mp4' in evidence.namelist()
            shutil.copyfile(receipt_file,output/'strategy-offline-receipt.json')
            shutil.copyfile(receipt_file.parent/'evidence.zip',output/'strategy-offline-evidence.zip')
        assert client.get('/api/runs/'+source['id']).json()==source_before
        assert len(client.get('/api/runs').json())==len(runs), 'Export/offline execution mutated central runs'

    errors=[]
    linux = next(run for run in runs if run['platform']=='linux' and run['status']=='waiting_worker')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge',headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1100},base_url=BASE,
                                permissions=['clipboard-read','clipboard-write'])
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('/#strategy',wait_until='networkidle')
        expect(page.locator('#view-strategy')).to_be_visible()
        expect(page.locator('.strategy-platforms>a')).to_have_count(3)
        for kind in ('windows','macos','linux'):
            page.locator(f'.strategy-platforms>a[href="#strategy/{kind}"]').click()
            expect(page.locator('#strategy-download')).to_have_attribute('href',f'/api/strategies/{kind}/kit?')
            expect(page.locator('#strategy-include')).to_be_disabled()
        page.goto(f'/#strategy/linux/{linux["id"]}')
        expect(page.locator('#strategy-run')).to_have_value(linux['id'])
        page.locator('#strategy-include').check()
        expect(page.locator('#strategy-download')).to_have_attribute('href',f'/api/strategies/linux/kit?run_id={linux["id"]}&include_package=true')
        with page.expect_download() as waiting:
            page.locator('#strategy-download').click()
        path = output/'strategy-linux-handoff.zip'
        waiting.value.save_as(path)
        with zipfile.ZipFile(path) as archive:
            manifest=json.loads(archive.read('scenario.json'))
            assert manifest['source_run_id']==linux['id']
            assert manifest['package']['file'] in archive.namelist()
        page.locator('#strategy-copy').click()
        invitation=page.evaluate('navigator.clipboard.readText()')
        assert linux['package']['sha256'] in invitation and 'Linux' in invitation
        expect(page.locator('#toast')).to_be_hidden(timeout=5000)
        page.screenshot(path=str(output/'strategy-desktop.png'),full_page=True)
        for width in (768,390):
            page.set_viewport_size({'width':width,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(output/'strategy-mobile.png'),full_page=True)
        page.goto('/#overview')
        expect(page.locator('#view-overview .heading-actions a[href="#strategy"]')).to_be_visible()
        expect(page.locator('#workspace-evidence [data-platform="linux"] a[href^="#strategy/"]')).to_be_visible(timeout=10000)
        page.locator('#workspace-evidence [data-platform="linux"] a[href^="#strategy/"]').click()
        expect(page.locator('#strategy-run')).to_have_value(linux['id'])
        expect(page.locator('#strategy-include')).not_to_be_checked()
        assert not errors,errors
        browser.close()
    (output/'strategy-validation.json').write_text(json.dumps({
        'source_run_id':source['id'],'offline_windows_status':receipt['execution_status'],
        'review_status':receipt['review_status'],'central_runs_unchanged':True,
        'exported_linux_run_id':linux['id'],'linux_executed':False,'macos_executed':False,
        'browser_errors':errors,'checks':['three platform strategies','bound ZIP with optional build',
            'independent Windows execution from exported runtime','preflight without launch','evidence and receipt',
            'invitation copy','desktop and mobile','waiting platform handoff link']},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Strategy delivery passed: exported Windows kit executed independently; Linux/Mac strategies exported, not executed.')


if __name__=='__main__':
    main()
