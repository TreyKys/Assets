							continue;
						}
						goto case 13;
					case 4:
						if (num4 <= App.Services.Banking.Document.GetMaximumAttachmentSize())
						{
							string text = registerConversationUIProcess.e();
							this.m_d = new AttachmentDto
							{
								AttachmentID = Guid.NewGuid(),
								Content = registerConversationUIProcess.SelectOrScanDocumentUIProcess.FileContent,
								FileName = text,
								FileExtension = Path.GetExtension(text).ToLower(),
								FileSize = registerConversationUIProcess.SelectOrScanDocumentUIProcess.FileContent.Length.ToString()
							};
							taskAwaiter2 = App.Services.Communication.CreateAttachment(this.m_d.ToFileInfo(), "MESSAGE").GetAwaiter();
							num = 6;
							num3 = num;
						}
						else
						{
