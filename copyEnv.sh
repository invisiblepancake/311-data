echo REACT_APP_MAPBOX_TOKEN=$REACT_APP_MAPBOX_TOKEN > .env
echo DB_URL=$DB_URL >> .env
echo MIXPANEL_ENABLED=$MIXPANEL_ENABLED >> .env
echo MIXPANEL_TOKEN_PROD=$MIXPANEL_TOKEN_PROD >> .env
echo MIXPANEL_TOKEN_DEV=$MIXPANEL_TOKEN_DEV >> .env
webpack
node server.js
