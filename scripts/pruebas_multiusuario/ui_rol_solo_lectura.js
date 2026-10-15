const { chromium } = require('playwright')
const PW='Clave-Segura-Test-8841'
async function api(page,m,url,body){ return page.evaluate(async([m,url,body])=>{const t=(await(await fetch('/api/csrf-token',{credentials:'include'})).json()).csrf_token;const r=await fetch(url,{method:m,credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':t},body:body?JSON.stringify(body):undefined});let j=null;try{j=await r.json()}catch{};return {s:r.status,j}},[m,url,body]) }
async function reg(b,u,mobile){ const ctx=await b.newContext(mobile?{viewport:{width:390,height:844},isMobile:true,hasTouch:true}:{viewport:{width:1280,height:800}}); const page=await ctx.newPage()
  await page.goto('http://127.0.0.1:3000/',{waitUntil:'networkidle'}); await page.click('text=Crea una'); const i=page.locator('input:visible'); await i.nth(0).fill(u); await i.nth(1).fill(PW); await page.locator('input[type=checkbox]').check(); await page.click('button[type=submit]'); await page.waitForURL('**/dashboard'); return page }
;(async()=>{
  const b=await chromium.launch({executablePath:process.env.CHROMIUM||undefined,args:['--no-sandbox','--disable-dev-shm-usage']})
  const t=Math.random().toString(36).slice(2,6); const R=[]; const ok=(n,c)=>{R.push(c); console.log(c?'  ok ':'  FALLO',n)}
  const A=await reg(b,'roA_'+t,false), V=await reg(b,'roV_'+t,true)
  await api(A,'POST','/api/hogares',{nombre:'Casa RO'}); const h=(await api(A,'GET','/api/hogares')).j; const hid=(h.propias||h.data.propias)[0].id
  await api(A,'POST',`/api/hogares/${hid}/compartir`,{usuario:'roV_'+t,nivel:'ver'})
  const inv=(await api(V,'GET','/api/hogares/invitaciones-pendientes')).j; await api(V,'POST','/api/hogares/aceptar-invitacion/'+(inv.data||inv)[0].codigo_invitacion); await api(V,'POST',`/api/hogares/${hid}/seleccionar`)
  await api(A,'POST','/api/productos',{nombre:'Solo lectura',cantidad:2,categoria:'Otros'})
  for(const r of ['/dashboard','/dashboard/shopping','/dashboard/gastos','/dashboard/recetas']){ await V.goto('http://127.0.0.1:3000'+r,{waitUntil:'networkidle'}); await V.waitForTimeout(500)
    const botones=await V.locator('button[aria-label="Añadir"], button[aria-label="Nuevo gasto"], button[aria-label="Nueva receta"]').count()
    ok(`rol ver (movil) no ve botones de alta en ${r}`,botones===0) }
  await V.goto('http://127.0.0.1:3000/dashboard',{waitUntil:'networkidle'}); ok('rol ver ve el producto',await V.locator('text=Solo lectura').count()>0)
  await A.goto('http://127.0.0.1:3000/dashboard',{waitUntil:'networkidle'}); ok('propietario (escritorio) si ve "Añadir Producto"',await A.locator('text=Añadir Producto').count()>0)
  console.log(`\nROLES ${R.filter(Boolean).length}/${R.length}`); await b.close()
})()
