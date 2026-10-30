import {test,expect} from '@playwright/test';
test('generate, inspect five views, repair absence, publish and persist',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.getByRole('heading',{name:'A clear plan for every day.'})).toBeVisible();
 await page.getByRole('button',{name:/^Generate (roster|new version)$/}).click();
 await expect(page.getByText('Valid draft',{exact:true})).toBeVisible({timeout:120000});
 await page.screenshot({path:'../docs/roster-desktop.png',fullPage:true});
 for(const view of ['Pod','Brand','Process','Employee','Company']){
  await page.getByRole('button',{name:view,exact:true}).click();
  if(view!=='Company'){await page.getByLabel(`${view} filter`).selectOption({index:1});}
  await expect(page.locator('.roster-table').first()).toBeVisible();
 }
 await page.getByRole('button',{name:/Aarav Mehta, 2026-11-\d+, work/}).first().click();
 await page.getByLabel('Find a repair while preserving other dates').uncheck();
 await page.getByRole('button',{name:'Preview change',exact:true}).click();
 await expect(page.getByText('This change cannot be safely applied')).toBeVisible({timeout:120000});
 await expect(page.getByRole('button',{name:'Approve & apply changes'})).toBeDisabled();
 await page.getByLabel('Find a repair while preserving other dates').check();
 await page.getByRole('button',{name:'Preview change',exact:true}).click();
 await expect(page.getByText('Validated proposal — ready for your approval')).toBeVisible({timeout:120000});
 await page.getByRole('button',{name:'Approve & apply changes'}).click();
 await expect(page.getByText('Change applied. Unaffected dates preserved.')).toBeVisible();
 await page.getByRole('button',{name:'Publish',exact:true}).click();
 await expect(page.getByText('Published',{exact:true})).toBeVisible();
 await page.reload();await expect(page.getByText('Published',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Validation centre'}).click();
 await expect(page.getByText('No mandatory violations',{exact:true})).toBeVisible();
 expect(errors).toEqual([]);
});
test('management form and mobile layout',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Organisation & rules',exact:true}).click();
 await page.getByRole('button',{name:'Processes',exact:true}).click();
 await page.getByRole('button',{name:'Add processes'}).click();
 const name='Demo returns '+Date.now();await page.getByLabel('Process name').fill(name);
 await page.getByRole('button',{name:'Save changes'}).click();
 await page.getByLabel('Search records').fill(name);await expect(page.getByRole('cell',{name,exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Edit',exact:true}).click();await page.getByLabel('Active',{exact:true}).uncheck();
 await page.getByRole('button',{name:'Save changes'}).click();
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Monthly roster'}).click();
 await page.screenshot({path:'../docs/roster-mobile.png',fullPage:true});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBeTruthy();
});

