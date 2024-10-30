"use client";

import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';

import React, { useRef, useState } from 'react';
import { styled, ThemeProvider, createTheme } from '@mui/material/styles';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';

import StakeholderList from './stakeholders/stakeholders';
import CostList from './costs/cost';
import RelevantDocumentList from './docs/docs';
import Chat from './chat/chat';
import CommunityManager from './community-manager/community-manager';
import { Container, Grid } from '@mui/material';
import { HubConnectionBuilder, HubConnection, LogLevel } from '@microsoft/signalr';

import { v4 as uuidv4 } from 'uuid';

type SignalRMessage = {
  userId: string;
  message: string;
  agent: string;
};

export default function Marketing() {
  const Item = styled(Paper)(({ theme }) => ({
    backgroundColor: theme.palette.mode === 'dark' ? '#1A2027' : '#fff',
    ...theme.typography.body2,
    padding: theme.spacing(0),
    textAlign: 'center',
    color: theme.palette.text.secondary,
  }));

  // Add this style
  const Background = styled('div')({
    backgroundImage: `url(/static/background1.webp)`,
    backgroundRepeat: 'no-repeat',
    backgroundSize: 'cover',
    height: '100vh',
  });
  
  const [userId, setUserId] = React.useState<string>(uuidv4());
  const [connection, setConnection] = React.useState<HubConnection>();
  const [messages, setMessages] = React.useState<{ sender: string; text: any; }[]>([]);

  //Community manager state
  
  const [ article, setArticle ] = useState<string>('');
  const [ imgUrl, setImgUrl ] = useState<string>('');
  const [ communityManagerOpen, setCommunityManagerOpen ] = useState<boolean>(false);

  const createSignalRConnection = async (userId: string) => {
    try {
      console.log(`[MainPage] Reading environment variables [${process.env.NEXT_PUBLIC_BACKEND_URI}]`);
      var uri = process.env.NEXT_PUBLIC_BACKEND_URI
        ? process.env.NEXT_PUBLIC_BACKEND_URI
        : 'http://localhost:5244';
      
      uri = new URL('articlehub', uri).href;
      console.log(`[MainPage] Connecting to [${uri}]`);
      // initi the connection
      const connection = new HubConnectionBuilder()
        .withUrl(uri, {withCredentials: false})
        .configureLogging(LogLevel.Information)
        .build();

      //setup handler
      connection.on('ReceiveMessage', (message: SignalRMessage) => {
        console.log(`[MainPage][${message.userId}] Received message from ${message.agent}: ${message.message}`);
        if (message.agent === 'Chat') {
          const newMessage = { sender: 'Writer', text: message.message };
          setMessages(prevMessages => [...prevMessages, newMessage]);
        }
        if (message.agent === 'Auditor') {
          const newMessage = { sender: 'Auditor', text: message.message };
          setMessages(prevMessages => [...prevMessages, newMessage]);
        }
        if (message.agent === 'CommunityManager') {
          setArticle(message.message);
          const newMessage = { sender: message.agent, text: 'Community Manager: ' + message.message };
          setMessages(prevMessages => [...prevMessages, newMessage]);
        }
        if (message.agent === 'GraphicDesigner') {
          setImgUrl(message.message);
          const newMessage = { sender: message.agent, text: 'Graphic Designer: Check the image I created!'};
          setMessages(prevMessages => [...prevMessages, newMessage]);
        }
      });

      connection.onclose(async () => {
        console.log(`[MainPage] Connection closed.`);

        try {
          await connection.start();
          console.log(`Connection ID: ${connection.connectionId}`);
          await connection.invoke('ConnectToAgent', userId);
          console.log(`[MainPage] Connection re-established.`);
        } catch (error) {
          console.error(error);
        }
      });

      await connection.start();
      console.log(`Connection ID: ${connection.connectionId}`);
      await connection.invoke('ConnectToAgent', userId);

      setConnection(connection);
      console.log(`[MainPage] Connection established.`);
    } catch (error) {
      console.error(error);
    }
  };

  const setMessagesInUI = async (messages: { sender: string; text: any; }[]) => {
    await setMessages(messages);
  }

  const sendMessage = async (message: string, agent: string) => {
    if (connection) {
      const frontEndMessage:SignalRMessage = { 
        userId: userId, 
        message: message,
        agent: agent
      };
      console.log(`[MainPage][${{agent}}] Sending message: ${message}`);
      await connection.invoke('ProcessMessage', frontEndMessage);
      console.log(`[MainPage][${{agent}}] message sent`);
    } else {
      console.error(`[MainPage] Connection not established.`);
    }
  }

  React.useEffect(() => {
    createSignalRConnection(userId);
  }, []);

  const defaultTheme = createTheme({
    typography: {
      fontFamily: 'Helvetica, Arial, sans-serif',
    },
  });

  const rightPannelTheme = createTheme({
    typography: {
      fontFamily: 'Helvetica, Arial, sans-serif',
    },
    components: {
      MuiListItemButton: {
        defaultProps: {
          disableTouchRipple: true,
        },
      },
    },
    palette: {
      mode: 'dark',
      // primary: { main: 'rgb(102, 157, 246)' },
      // background: { paper: 'rgb(5, 30, 52)' },
      primary: { main: '#006BD6' },
      background: { paper: 'grey' },
    },
  });

  console.log(`[Marketing] Rendering.`);
  return (
    <ThemeProvider theme={defaultTheme}>
    <Background>
    <Container maxWidth="xl" disableGutters >
      <Grid container spacing={3}>
        <Grid item xs={6}>
          <Paper elevation={0} style={{ border: '1px solid #000' }}>
            <Chat messages={messages} setMessages={setMessagesInUI} sendMessage={sendMessage}/>
          </Paper>
        </Grid>
        <Grid item xs={6}>
          <Stack spacing={0}>
            <ThemeProvider theme={rightPannelTheme}>
              <Item>
                <Paper elevation={0}>
                  <StakeholderList />
                </Paper>
                <Divider />
              </Item>
              <Item>
                <Paper elevation={0}>
                  <CostList />
                </Paper>
                <Divider />
              </Item>
              <Item>
                <Paper elevation={0}>
                  <RelevantDocumentList />
                </Paper>
                <Divider />
              </Item>
              <Item>
                <Paper elevation={0}>
                  <CommunityManager article={article} open={communityManagerOpen} setOpen={setCommunityManagerOpen} imgUrl={imgUrl}/>
                </Paper>
                <Divider />
              </Item>
            </ThemeProvider>
          </Stack>
        </Grid>
      </Grid>
    </Container>
    </Background>
    </ThemeProvider>
  );
}