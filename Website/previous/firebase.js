(function () {
  const config = {
    apiKey: "AIzaSyCKc3EmsQUim9LQc29C0JiTPGj1ErvQY6I",
    authDomain: "vigil-15d90.firebaseapp.com",
    databaseURL: "https://vigil-15d90.firebaseio.com",
    projectId: "vigil-15d90",
    storageBucket: "vigil-15d90.appspot.com",
    messagingSenderId: "915294142360",
    appId: "1:915294142360:web:15e16c76f439bf885e35ed"
  };

  firebase.initializeApp(config);
}());

function resetData() {
  firebase.database().ref('Police').set(0);
  firebase.database().ref('Medical').set(0);
  firebase.database().ref('FireDept').set(0);
}

const pol = document.getElementById("police");
const dbRef = firebase.database().ref().child("Police");
dbRef.on("value", snap => pol.innerText = snap.val());
const med = document.getElementById("med");
const dbRef1 = firebase.database().ref().child("Medical");
dbRef1.on("value", snap => med.innerText = snap.val());
const fire = document.getElementById("fire");
const dbRef2 = firebase.database().ref().child("FireDept");
dbRef2.on("value", snap => fire.innerText = snap.val());
var storage = firebase.storage();
var storageRef = storage.ref();

storageRef.child('images/foo.jpg').getDownloadURL().then(function (url) {
  var test = url;
  document.getElementById("graph").src = test;

}).catch(function (error) {

});
storageRef.child('images/bar.jpg').getDownloadURL().then(function (url) {
  var test = url;
  document.getElementById("frame1").src = test;

}).catch(function (error) {

});
storageRef.child('images/foobar.jpg').getDownloadURL().then(function (url) {
  var test = url;
  document.getElementById("frame2").src = test;

}).catch(function (error) {

});