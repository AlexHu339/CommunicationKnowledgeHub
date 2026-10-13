from __future__ import annotations

import asyncio
import sys

from playwright.async_api import async_playwright


async def main() -> int:
    base=(sys.argv[1] if len(sys.argv)>1 else "http://127.0.0.1:8765").rstrip("/")
    paths=["/","/today","/map","/review","/notes","/competition","/instruments","/postgrad","/policies","/universities","/ai-links","/ocr","/generate","/updates","/review-queue","/media","/statistics","/settings","/ai-config","/capabilities","/usage","/data","/backups","/diagnostics"]
    failures=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        page=await browser.new_page()
        page.on("pageerror",lambda error: failures.append(f"pageerror: {error}"))
        page.on("console",lambda message: failures.append(f"console.{message.type}: {message.text}") if message.type=="error" else None)
        for path in paths:
            before=len(failures)
            response=await page.goto(base+path,wait_until="networkidle")
            root=await page.locator("#root").inner_text()
            if not response or response.status>=400 or not root.strip():failures.append(f"{path}: status={response.status if response else 'none'} root={len(root.strip())}")
            print(f"{path}: {'PASS' if len(failures)==before else 'FAIL'} root={len(root.strip())}")
        print("\nSPA CLICKS")
        await page.goto(base,wait_until="networkidle")
        for path in paths[1:]:
            before=len(failures)
            await page.locator(f'nav a[href="{path}"]').click()
            await page.wait_for_timeout(300)
            root=await page.locator("#root").inner_text()
            if not root.strip():failures.append(f"click {path}: empty root")
            print(f"click {path}: {'PASS' if len(failures)==before else 'FAIL'} root={len(root.strip())}")
        print("\nREVISITS")
        for path in ["/map","/statistics","/map","/today","/review-queue","/statistics"]:
            before=len(failures)
            await page.locator(f'nav a[href="{path}"]').click()
            await page.wait_for_timeout(500)
            root=await page.locator("#root").inner_text()
            if not root.strip():failures.append(f"revisit {path}: empty root")
            print(f"revisit {path}: {'PASS' if len(failures)==before else 'FAIL'} root={len(root.strip())}")
        print("\nNONSTANDARD SCROLLTO RETURN")
        nonstandard=await browser.new_page()
        nonstandard_errors=[]
        nonstandard.on("pageerror",lambda error: nonstandard_errors.append(f"pageerror: {error}"))
        nonstandard.on("console",lambda message: nonstandard_errors.append(f"console.{message.type}: {message.text}") if message.type=="error" else None)
        await nonstandard.add_init_script("Object.defineProperty(window,'scrollTo',{value:()=>({edgeCompatible:true}),writable:true,configurable:true})")
        await nonstandard.goto(base,wait_until="networkidle")
        for path in ["/today","/map","/ai-links","/settings","/today"]:
            before=len(nonstandard_errors)
            await nonstandard.locator(f'nav a[href="{path}"]').click()
            await nonstandard.wait_for_timeout(300)
            root=await nonstandard.locator("#root").inner_text()
            if not root.strip():nonstandard_errors.append(f"nonstandard-scrollTo {path}: empty root")
            print(f"nonstandard-scrollTo {path}: {'PASS' if len(nonstandard_errors)==before else 'FAIL'} root={len(root.strip())}")
        failures.extend(f"nonstandard-scrollTo {item}" for item in nonstandard_errors)
        await nonstandard.close()
        await browser.close()
    if failures:
        print("\nERRORS")
        for item in failures:print(item)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(asyncio.run(main()))
