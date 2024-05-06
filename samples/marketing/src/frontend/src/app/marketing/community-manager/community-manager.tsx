"use client";

import * as React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import { styled } from '@mui/material/styles';
import AppShortcut from '@mui/icons-material/AttachMoney';
import LoopIcon from '@mui/icons-material/Loop';
import { Card, CardContent, Typography } from '@mui/material';
import Image from 'next/image';

const FireNav = styled(List)<{ component?: React.ElementType }>({
  '& .MuiListItemButton-root': {
    paddingLeft: 24,
    paddingRight: 24,
  },
  '& .MuiListItemIcon-root': {
    minWidth: 0,
    marginRight: 16,
  },
  '& .MuiSvgIcon-root': {
    fontSize: 20,
  },
});

type CommunityManagerProps = {
  article: string;
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  imgUrl: string;
};

export default function CommunityManager({ article, open, setOpen, imgUrl }: CommunityManagerProps) {
  console.log(`[CommunityManager] Rendering. Url: '${imgUrl}'`);

  return (
    <Box sx={{ display: 'flex' }}>
      <FireNav component="nav" disablePadding>
        <Box
          sx={{
            //bgcolor: open ? 'rgba(71, 98, 130, 0.2)' : null,
            //pb: open ? 2 : 0,
          }}
        >
          <ListItemButton
            alignItems="flex-start"
            onClick={() => setOpen(!open)}
            sx={{
              px: 3,
              pt: 2.5,
              pb: open ? 0 : 2.5,
              '&:hover, &:focus': { '& #arrowdownicon': { opacity: open ? 1 : 0 } },
            }}
          >
            <ListItemIcon sx={{ my: 0, opacity: 1, class: "menuicon" }}>
              <AppShortcut />
            </ListItemIcon>
            <ListItemText
              primary="Social Media posts"
              primaryTypographyProps={{
                fontSize: 15,
                fontWeight: 'medium',
                lineHeight: '20px',
                mb: '2px',
              }}
              secondary="Posts in social media"
              secondaryTypographyProps={{
                noWrap: true,
                fontSize: 12,
                lineHeight: '16px',
                color: open ? 'rgba(0,0,0,0)' : 'rgba(255,255,255,0.5)',
              }}
              sx={{ my: 0 }}
            />
            <KeyboardArrowDown
              id="arrowdownicon"
              sx={{
                mr: -1,
                opacity: 0,
                transform: open ? 'rotate(-180deg)' : 'rotate(0)',
                transition: '0.2s',
              }}
            />
          </ListItemButton>
          {open && (
            article === '' || article === null ? (
              <Box>
                <LoopIcon
                  sx={{
                    animation: "spin 2s linear infinite",
                    "@keyframes spin": {
                      "0%": {
                        transform: "rotate(360deg)",
                      },
                      "100%": {
                        transform: "rotate(0deg)",
                      },
                    },
                  }}
                />
              </Box>
            ) : (
              <Card>
                <CardContent>
                    <Typography variant="h5" component="div">
                      Social media posts on X
                    </Typography>
                    <p>{article}</p>
                    {imgUrl && (
                      <div style={{ width: '100%', height: '500px', position: 'relative' }}>
                        <Image 
                          layout='fill'
                          objectFit='cover'
                          src={imgUrl} 
                          alt="Graphic designer is working on an image ..." 
                        />
                      </div>
                    )}
                  </CardContent>
              </Card>
            )
          )}
        </Box>
      </FireNav>
    </Box>
  );
}