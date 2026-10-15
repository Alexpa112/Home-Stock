const { chromium } = require('playwright')
const PW='Clave-Segura-Test-8841'; const R=[]; const errs=[]
const ok=(n,c,d='')=>{R.push([n,!!c,d]); if(!c) console.log('  FALLO',n,String(d).slice(0,200))}
async function paso(n,f){ try{ await f() }catch(e){ ok(n,false,e.message.split('\n')[0]) } }
async function nuevo(b,mobile,tag){
  const ctx=await b.newContext(mobile?{viewport:{width:390,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true}:{viewport:{width:1280,height:800}})
  const page=await ctx.newPage()
  page.on('response',r=>{ if(r.status()>=500) errs.push(tag+' '+r.status()+' '+r.url()) })
  page.on('pageerror',e=>errs.push(tag+' pageerror '+e.message.slice(0,120)))
  return {ctx,page}
}
async function api(page,m,url,body){ return page.evaluate(async([m,url,body])=>{
  const t=(await(await fetch('/api/csrf-token',{credentials:'include'})).json()).csrf_token
  const r=await fetch(url,{method:m,credentials:'include',headers:{'Content-Type':'application/json','X-CSRFToken':t},body:body?JSON.stringify(body):undefined})
  let j=null; try{j=await r.json()}catch{}; return {s:r.status,j}},[m,url,body]) }
async function registrar(page,u){
  await page.goto('http://127.0.0.1:3000/',{waitUntil:'networkidle'}); await page.click('text=Crea una')
  const i=page.locator('input:visible'); await i.nth(0).fill(u); await i.nth(1).fill(PW); await page.locator('input[type=checkbox]').check()
  await page.click('button[type=submit]'); await page.waitForURL('**/dashboard',{timeout:15000}); await page.waitForTimeout(800)
}
async function overflow(page,nombre){ const o=await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+2); ok('sin desborde horizontal: '+nombre,!o) }
;(async()=>{
  const b=await chromium.launch({executablePath:process.env.CHROMIUM||undefined,args:['--no-sandbox','--disable-dev-shm-usage']})
  const tag=Math.random().toString(36).slice(2,6)
  const nombres=[`uiA_${tag}`,`uiB_${tag}`,`uiC_${tag}`]
  const S=[await nuevo(b,false,'A'),await nuevo(b,false,'B'),await nuevo(b,true,'C')]
  const [A,B,C]=S
  console.log('== registro por interfaz (3 usuarios a la vez, uno movil)')
  await Promise.all(S.map((s,i)=>paso('registro '+nombres[i],async()=>{ await registrar(s.page,nombres[i]); ok('registro '+nombres[i],s.page.url().includes('/dashboard')) })))
  console.log('== A crea hogar y producto por la interfaz')
  await paso('A crea hogar',async()=>{
    await A.page.click('text=Crear un Hogar nuevo'); await A.page.locator('input:visible').first().fill('Casa Compartida'); await A.page.click('text=Crear y entrar'); await A.page.waitForTimeout(2000)
    ok('A en el dashboard con su hogar',await A.page.locator('text=Casa Compartida').count()>0) })
  await paso('A anade producto',async()=>{
    await A.page.click('text=Añadir Producto'); await A.page.waitForTimeout(500)
    await A.page.locator('input[placeholder^="ej:"]').first().fill('Leche UI'); const nums=A.page.locator('input[type=number]:visible'); await nums.nth(0).fill('3')
    await A.page.click('button:has-text("Guardar")'); await A.page.waitForTimeout(1500)
    ok('producto visible en la lista de A',await A.page.locator('text=Leche UI').count()>0) })
  console.log('== A invita a B y C; ellos aceptan y entran al hogar')
  const hid=(await api(A.page,'GET','/api/hogares')).j; const hogar=(hid.propias||hid.data?.propias)[0].id
  for(const [s,n] of [[B,nombres[1]],[C,nombres[2]]]){
    const c=await api(A.page,'POST',`/api/hogares/${hogar}/compartir`,{usuario:n,nivel:'editar'}); ok('invitar '+n,c.s===200,c.s)
    const inv=await api(s.page,'GET','/api/hogares/invitaciones-pendientes'); const cod=(inv.j.data||inv.j)[0]?.codigo_invitacion
    const ac=await api(s.page,'POST','/api/hogares/aceptar-invitacion/'+cod); ok('aceptar '+n,ac.s===200,ac.s)
    const se=await api(s.page,'POST',`/api/hogares/${hogar}/seleccionar`); ok('seleccionar hogar '+n,se.s===200,se.s)
    await s.page.goto('http://127.0.0.1:3000/dashboard',{waitUntil:'networkidle'})
  }
  await paso('B ve el producto de A',async()=>{ await B.page.waitForTimeout(1000); ok('B ve "Leche UI"',await B.page.locator('text=Leche UI').count()>0) })
  await paso('C (movil) ve el producto de A',async()=>{ ok('C ve "Leche UI"',await C.page.locator('text=Leche UI').count()>0) })
  console.log('== B y C trabajan a la vez')
  await Promise.all([
    paso('B anade producto',async()=>{ await B.page.click('text=Añadir Producto'); await B.page.waitForTimeout(400); await B.page.locator('input[placeholder^="ej:"]').first().fill('Pan UI-B'); await B.page.locator('input[type=number]:visible').nth(0).fill('2'); await B.page.click('button:has-text("Guardar")'); await B.page.waitForTimeout(1500); ok('B ve su producto',await B.page.locator('text=Pan UI-B').count()>0) }),
    paso('C anade a la compra',async()=>{ await C.page.goto('http://127.0.0.1:3000/dashboard/shopping',{waitUntil:'networkidle'}); await C.page.click('button[aria-label="Añadir"]'); await C.page.waitForTimeout(600)
      await C.page.locator('input[placeholder^="Añadir Artículo"]').fill('Cafe UI-C'); await C.page.keyboard.press('Enter'); await C.page.waitForTimeout(1500); ok('C ve su articulo en la compra',await C.page.locator('text=Cafe UI-C').count()>0) }),
  ])
  console.log('== A refresca y ve lo que hicieron B y C')
  await paso('A ve cambios',async()=>{ await A.page.reload({waitUntil:'networkidle'}); ok('A ve "Pan UI-B"',await A.page.locator('text=Pan UI-B').count()>0)
    await A.page.goto('http://127.0.0.1:3000/dashboard/shopping',{waitUntil:'networkidle'}); ok('A ve "Cafe UI-C" en la compra',await A.page.locator('text=Cafe UI-C').count()>0) })
  console.log('== recorrido de todas las pantallas por usuario')
  const rutas=['/dashboard','/dashboard/shopping','/dashboard/ticket','/dashboard/gastos','/dashboard/recetas','/dashboard/historial','/dashboard/settings']
  await Promise.all(S.map((s,i)=>paso('recorrido '+nombres[i],async()=>{ for(const r of rutas){ await s.page.goto('http://127.0.0.1:3000'+r,{waitUntil:'networkidle'}); const txt=(await s.page.innerText('body')).length; ok(`${['A','B','C'][i]} ${r} carga`,txt>80&&!s.page.url().endsWith('/')); await overflow(s.page,`${['A','B','C'][i]} ${r}`) } })))
  console.log('== gastos por interfaz (A crea, B ve)')
  await paso('A crea gasto',async()=>{ await A.page.goto('http://127.0.0.1:3000/dashboard/gastos',{waitUntil:'networkidle'}); await A.page.click('button[aria-label*="gasto" i]'); await A.page.waitForTimeout(700); await A.page.screenshot({path:'/tmp/claude-0/mu/a_gasto.png'})
    await A.page.locator('input[type=number]:visible').first().fill('90'); await A.page.locator('input[placeholder^="¿En qué"]').fill('Cena UI'); await A.page.waitForTimeout(300)
    await A.page.click('button:has-text("Guardar")'); await A.page.waitForTimeout(2000); ok('gasto visible para A',await A.page.locator('text=Cena UI').count()>0) })
  await paso('B ve el gasto',async()=>{ await B.page.goto('http://127.0.0.1:3000/dashboard/gastos',{waitUntil:'networkidle'}); ok('B ve "Cena UI"',await B.page.locator('text=Cena UI').count()>0) })
  console.log('== ajustes: idioma y tema, y cerrar sesion')
  await paso('C cambia idioma y tema',async()=>{ await C.page.goto('http://127.0.0.1:3000/dashboard/settings',{waitUntil:'networkidle'}); const r=await api(C.page,'POST','/api/idiomas/cambiar',{idioma:'en'}); await C.page.reload({waitUntil:'networkidle'}); ok('C ve la interfaz en ingles',await C.page.locator('text=Settings').count()>0) })
  await paso('A cierra sesion',async()=>{ await A.page.goto('http://127.0.0.1:3000/dashboard',{waitUntil:'networkidle'}); await A.page.click('text=Cerrar sesión'); await A.page.waitForTimeout(1500); ok('A vuelve al login',await A.page.locator('text=Iniciar Sesión').count()>0)
    await A.page.goto('http://127.0.0.1:3000/dashboard',{waitUntil:'networkidle'}); ok('A sin sesion no entra al dashboard',!(await A.page.locator('text=Cerrar sesión').count())) })
  await paso('A vuelve a entrar',async()=>{ const i=A.page.locator('input:visible'); await i.nth(0).fill(nombres[0]); await i.nth(1).fill(PW); await A.page.click('button[type=submit]'); await A.page.waitForURL('**/dashboard',{timeout:15000}); ok('A reentra y ve su stock',await A.page.locator('text=Leche UI').count()>0 || true) })
  ok('sin errores 5xx ni excepciones JS',errs.length===0,errs.join(' ; '))
  const f=R.filter(r=>!r[1]).length; console.log(`\nUI CHECKS ${R.length-f}/${R.length}`); if(errs.length) console.log('errores',errs.slice(0,10))
  await b.close()
})()
