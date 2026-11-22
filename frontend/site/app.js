// La page parle à l'API par Traefik. Les adresses sont relatives (« api/… », sans / devant) :
// la page marche donc à n'importe quelle adresse, http://localhost:8083/ ou derrière un autre proxy.
// Les données s'affichent avec textContent, jamais innerHTML : un nom de produit ne devient pas du code.

const prixFCFA = new Intl.NumberFormat("fr-FR");
const date = new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium", timeStyle: "short" });

function element(balise, classe, texte) {
  const e = document.createElement(balise);
  if (classe) e.className = classe;
  if (texte !== undefined) e.textContent = texte;
  return e;
}

function carte(produit) {
  const li = element("li", "produit");
  li.append(
    element("span", "produit-nom", produit.nom),
    element("span", "produit-prix", `${prixFCFA.format(produit.prix)} FCFA`),
    element("span", "produit-date", `ajouté le ${date.format(new Date(produit.cree_le))}`),
  );
  return li;
}

async function chargerProduits() {
  const liste = document.getElementById("produits");
  const source = document.getElementById("source");
  try {
    const reponse = await fetch("api/produits");
    if (!reponse.ok) throw new Error(`l'API répond ${reponse.status}`);
    const produits = await reponse.json();
    liste.replaceChildren(...produits.map(carte));
    const cache = reponse.headers.get("X-Cache") === "HIT" ? "depuis le cache Redis (HIT)" : "depuis PostgreSQL (MISS)";
    source.textContent = `${produits.length} produits, ${cache} · servi par ${reponse.headers.get("X-Servi-Par") ?? "?"}`;
  } catch (erreur) {
    liste.replaceChildren();
    source.textContent = `Impossible de lire les produits : ${erreur.message}`;
  }
}

async function compterVisite() {
  const visites = document.getElementById("visites");
  try {
    const reponse = await fetch("api/visites", { method: "POST" });
    const corps = await reponse.json();
    visites.textContent = reponse.ok ? `${prixFCFA.format(corps.visites)} visites` : "compteur indisponible";
  } catch {
    visites.textContent = "compteur indisponible";
  }
}

async function chargerEtat() {
  const voyants = document.getElementById("voyants");
  let etat = { etat: "ko", base: "?", cache: "?" };
  try {
    etat = await (await fetch("api/sante")).json();
  } catch {
    // l'API ne répond pas du tout : les voyants restent au rouge
  }
  const voyant = (nom, valeur) => element("li", valeur === "ok" ? "voyant ok" : "voyant ko", `${nom} : ${valeur}`);
  voyants.replaceChildren(voyant("API", etat.etat), voyant("base", etat.base), voyant("cache", etat.cache));
}

async function ajouter(evenement) {
  evenement.preventDefault();
  const formulaire = evenement.currentTarget;
  const message = document.getElementById("message");
  const produit = { nom: formulaire.nom.value.trim(), prix: Number(formulaire.prix.value) };
  try {
    const reponse = await fetch("api/produits", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(produit),
    });
    const corps = await reponse.json();
    if (!reponse.ok) throw new Error(corps.erreur ?? `l'API répond ${reponse.status}`);
    message.textContent = `Ajouté : ${corps.nom}`;
    formulaire.reset();
    await chargerProduits();
  } catch (erreur) {
    message.textContent = `Refusé : ${erreur.message}`;
  }
}

document.getElementById("formulaire").addEventListener("submit", ajouter);
document.getElementById("recharger").addEventListener("click", chargerProduits);
compterVisite();
chargerProduits();
chargerEtat();
setInterval(chargerEtat, 15000);
