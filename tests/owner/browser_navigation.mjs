// Exercise the visible navigation surface at either desktop or mobile width.
export async function workspaceNav(page,name){
 if(await page.locator('#workspace-menu').isVisible())await page.locator('#workspace-menu').click();
 await page.locator(`[data-view="${name}"]`).click();
}
