# Implementation Plan

- [x] 1. Implementează Caption Manager centralizat


  - Creează funcția `create_safe_caption()` în app.py cu truncare inteligentă și escapare HTML
  - Implementează logica de prioritizare a informațiilor (titlu > creator > durată > descriere)
  - Adaugă gestionarea caracterelor Unicode, emoticoanelor și diacriticelor românești
  - Implementează buffer de siguranță pentru limitele Telegram (1000 caractere în loc de 1024)
  - _Requirements: 1.2, 1.3, 5.1, 5.2, 5.3, 5.4, 5.5_



- [ ] 2. Actualizează funcțiile existente să folosească Caption Manager
  - Modifică `handle_message()` în app.py să folosească noua funcție de caption
  - Actualizează `process_download()` în bot.py să folosească Caption Manager
  - Înlocuiește toate instanțele de creare manuală a caption-urilor cu funcția centralizată


  - Testează compatibilitatea cu funcționalitatea existentă
  - _Requirements: 1.1, 1.2, 5.5_

- [ ] 3. Implementează Error Handler cu clasificare și retry logic
  - Creează clasa `ErrorHandler` cu metode pentru clasificarea erorilor
  - Implementează detectarea erorilor de caption prea lung și retry automat cu caption truncat


  - Adaugă gestionarea erorilor specifice platformelor (privat, indisponibil, parsing)
  - Implementează retry cu exponential backoff pentru erori de rețea
  - Creează mesaje de eroare prietenoase pentru utilizatori
  - _Requirements: 1.4, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4. Optimizează configurațiile pentru Render free tier


  - Reduce timeout-urile în app.py pentru webhook și connection pool
  - Optimizează configurațiile yt-dlp pentru utilizare redusă de memorie
  - Implementează cleanup automat și agresiv al fișierelor temporare
  - Adaugă configurații specifice pentru limitările CPU și memorie Render
  - Testează stabilitatea pe Render free tier cu multiple cereri
  - _Requirements: 3.1, 3.2, 3.3, 3.5_



- [ ] 5. Îmbunătățește strategiile de fallback pentru Facebook
  - Actualizează `try_facebook_fallback()` cu configurații noi pentru 2025
  - Implementează normalizarea URL-urilor Facebook pentru noile formate
  - Adaugă multiple user agents și headers pentru evitarea detecției


  - Implementează strategii progresive de calitate (720p → 480p → 360p)
  - Testează cu diverse tipuri de link-uri Facebook (share/v/, reel/, watch)
  - _Requirements: 2.3, 2.5, 6.1, 6.3_

- [ ] 6. Îmbunătățește gestionarea platformelor TikTok și Instagram
  - Actualizează configurațiile TikTok cu user agents mobili recenți


  - Implementează gestionarea îmbunătățită pentru Instagram Reels și IGTV
  - Adaugă strategii de fallback pentru Twitter/X cu noile formate de URL
  - Optimizează configurațiile pentru evitarea rate limiting-ului
  - _Requirements: 2.1, 2.2, 2.4, 2.5_



- [ ] 7. Implementează optimizarea calității și mărimii videoclipurilor
  - Adaugă logica de verificare a mărimii fișierului înainte de upload
  - Implementează redownload automat cu calitate mai mică pentru fișiere prea mari
  - Creează mesaje informative pentru utilizatori despre limitările de mărime
  - Adaugă progres indicators pentru descărcări lungi
  - Optimizează selecția formatului pentru echilibrul calitate/mărime


  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 8. Îmbunătățește gestionarea webhook-urilor și răspunsurilor Telegram
  - Optimizează funcțiile `safe_send_message()` și `safe_edit_message()` pentru stabilitate
  - Implementează gestionarea îmbunătățită a chat-urilor inaccesibile


  - Adaugă retry logic pentru operațiile Telegram API
  - Optimizează configurațiile bot pentru Render (connection pool, timeout-uri)
  - _Requirements: 3.4, 4.4_

- [ ] 9. Creează suite comprehensivă de teste
  - Implementează teste unitare pentru Caption Manager cu diverse caractere speciale



  - Creează teste pentru Error Handler cu simularea diverselor tipuri de erori
  - Adaugă teste de integrare pentru fluxul complet de descărcare pe toate platformele
  - Implementează teste pentru compatibilitatea cu Render free tier
  - Creează teste pentru gestionarea caracterelor Unicode și emoticoanelor
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 10. Implementează logging și monitoring îmbunătățit
  - Adaugă logging structurat pentru debugging în producție
  - Implementează metrici pentru success rate per platformă
  - Creează alerting pentru erori critice și utilizare excesivă de resurse
  - Adaugă monitoring pentru performanța pe Render free tier
  - _Requirements: 4.4_

- [ ] 11. Testează și validează toate cerințele
  - Rulează teste locale cu videoclipuri cu descrieri lungi de pe toate platformele
  - Testează gestionarea caracterelor speciale, diacriticelor și emoticoanelor
  - Validează funcționarea pe Render free tier cu limitările de resurse
  - Testează scenarii de eroare și mesajele pentru utilizatori
  - Verifică că toate cerințele din requirements.md sunt îndeplinite
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 12. Pregătește deployment pe Render
  - Actualizează documentația de deployment cu noile configurații
  - Creează script de verificare post-deployment
  - Implementează rollback strategy în caz de probleme
  - Testează deployment pe Render cu configurațiile de producție
  - Monitorizează stabilitatea și performanța după deployment
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_