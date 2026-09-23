using System;
using System.CodeDom.Compiler;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Runtime.CompilerServices;
using System.Threading;
using Newtonsoft.Json;

namespace BVB.EOS.OnlineBanking.UI.Mobile.Services.ApiServices.App.Contracts;

[GeneratedCode("NJsonSchema", "14.4.0.0 (NJsonSchema v11.3.2.0 (Newtonsoft.Json v13.0.0.0))")]
public class CreateUserDefinedNotificationDto : INotifyPropertyChanged
{
	private Guid? a;

	private string b;

	private string c;

	private decimal? d;

	private string e;

	private string f;

	private string g;

	private bool h;

	[CompilerGenerated]
	private PropertyChangedEventHandler i;

	[JsonProperty("accountID", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public Guid? AccountID
	{
		get
		{
			short num = 1747;
			short num2 = num;
			num = 1747;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return a;
			}
		}
		set
		{
			int num = default(int);
			Guid? guid = default(Guid?);
			Guid? guid2 = default(Guid?);
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 7:
						if (guid.HasValue != guid2.HasValue)
						{
							short num2 = 1;
							num = num2;
						}
						else
						{
							short num2 = 3;
							num = num2;
						}
						continue;
					case 5:
					{
						a = value;
						RaisePropertyChanged("AccountID");
						short num2 = 2;
						num = num2;
						continue;
					}
					case 2:
						return;
					case 6:
					{
						short num2 = -15797;
						short num3 = num2;
						num2 = -15797;
						switch (num3 == num2)
						{
						default:
							num2 = 0;
							if (num2 == 0)
							{
							}
							return;
						case false:
						case true:
							break;
						}
						goto case 0;
					}
					case 1:
					{
						short num2 = 0;
						num = num2;
						continue;
					}
					case 0:
					{
						short num2 = 5;
						num = num2;
						continue;
					}
					case 8:
						if (!(guid.GetValueOrDefault() != guid2.GetValueOrDefault()))
						{
							return;
						}
						goto case 0;
					case 3:
						if (guid.HasValue)
						{
							short num2 = 8;
							num = num2;
						}
						else
						{
							short num2 = 4;
							num = num2;
						}
						continue;
					case 4:
					{
						short num2 = 1;
						if (num2 != 0)
						{
						}
						num2 = 6;
						num = num2;
						continue;
					}
					}
					break;
				}
				goto case 0;
			case 0:
			{
				guid = a;
				guid2 = value;
				short num2 = 7;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("notificationTypeCOID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public string NotificationTypeCOID
	{
		get
		{
			short num = 1326;
			short num2 = num;
			num = 1326;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return b;
			}
		}
		set
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = 0;
			int num2 = num;
			while (true)
			{
				num = 18782;
				short num3 = num;
				num = 18782;
				switch (num3 == num)
				{
				default:
					num = 0;
					if (num != 0)
					{
					}
					switch (num2)
					{
					case 0:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						break;
					case 2:
						b = value;
						RaisePropertyChanged("NotificationTypeCOID");
						num = 1;
						num2 = num;
						continue;
					case 1:
						return;
					}
					break;
				case false:
				case true:
					break;
				}
				if (b != value)
				{
					num = 2;
					num2 = num;
					continue;
				}
				break;
			}
		}
	}

	[JsonProperty("notificationCriteriumCOID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	[Required(AllowEmptyStrings = true)]
	public string NotificationCriteriumCOID
	{
		get
		{
			short num = 20527;
			short num2 = num;
			num = 20527;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return c;
			}
		}
		set
		{
			short num = 2;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 2:
					num = 1;
					if (num != 0)
					{
					}
					switch (0)
					{
					default:
						goto end_IL_0060;
					case 0:
						break;
					}
					goto default;
				default:
				{
					num = -438;
					short num3 = num;
					num = -438;
					switch (num3 == num)
					{
					default:
						num = 0;
						if (num != 0)
						{
						}
						if (!(c != value))
						{
							return;
						}
						goto case false;
					case false:
					case true:
						num = 1;
						num2 = num;
						break;
					}
					break;
				}
				case 1:
					c = value;
					RaisePropertyChanged("NotificationCriteriumCOID");
					num = 0;
					num2 = num;
					break;
				case 0:
					return;
					end_IL_0060:
					break;
				}
			}
		}
	}

	[JsonProperty("amountCriterium", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public decimal? AmountCriterium
	{
		get
		{
			short num = 32496;
			short num2 = num;
			num = 32496;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return d;
			}
		}
		set
		{
			int num = default(int);
			decimal? num4 = default(decimal?);
			decimal? num5 = default(decimal?);
			switch (0)
			{
			default:
				while (true)
				{
					switch (num)
					{
					case 0:
					{
						short num2 = 1;
						if (num2 != 0)
						{
						}
						if (!(num4 == num5))
						{
							num2 = 2;
							num = num2;
							continue;
						}
						return;
					}
					case 2:
					{
						d = value;
						RaisePropertyChanged("AmountCriterium");
						short num2 = 1;
						num = num2;
						continue;
					}
					case 1:
					{
						short num2 = 14182;
						short num3 = num2;
						num2 = 14182;
						switch (num3 == num2)
						{
						case false:
						case true:
							break;
						default:
							num2 = 0;
							if (num2 == 0)
							{
							}
							return;
						}
						goto case 2;
					}
					}
					break;
				}
				goto case 0;
			case 0:
			{
				num4 = d;
				num5 = value;
				short num2 = 0;
				num = num2;
				goto default;
			}
			}
		}
	}

	[JsonProperty("textCriterium", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string TextCriterium
	{
		get
		{
			short num = 13208;
			short num2 = num;
			num = 13208;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return e;
			}
		}
		set
		{
			short num = 0;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 0:
					switch (0)
					{
					default:
						goto end_IL_002c;
					case 0:
						break;
					}
					goto default;
				default:
				{
					if (!(e != value))
					{
						return;
					}
					num = 13384;
					short num3 = num;
					num = 13384;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 1;
						if (num != 0)
						{
						}
						num = 2;
						num2 = num;
						break;
					}
					break;
				}
				case 2:
					e = value;
					RaisePropertyChanged("TextCriterium");
					num = 1;
					num2 = num;
					break;
				case 1:
					return;
					end_IL_002c:
					break;
				}
			}
		}
	}

	[Required(AllowEmptyStrings = true)]
	[JsonProperty("statusCOID", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public string StatusCOID
	{
		get
		{
			short num = 1;
			if (num != 0)
			{
			}
			num = -8574;
			short num2 = num;
			num = -8574;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				return f;
			}
		}
		set
		{
			while (true)
			{
				short num = 2;
				int num2 = num;
				while (true)
				{
					switch (num2)
					{
					case 2:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						goto default;
					default:
						if (f != value)
						{
							num = 0;
							num2 = num;
							continue;
						}
						return;
					case 0:
						break;
					case 1:
						num = 1;
						if (num == 0)
						{
						}
						return;
					}
					num = -13488;
					short num3 = num;
					num = -13488;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						f = value;
						RaisePropertyChanged("StatusCOID");
						num = 1;
						num2 = num;
						continue;
					}
					break;
				}
			}
		}
	}

	[JsonProperty("notificationText", Required = Required.Default, NullValueHandling = NullValueHandling.Ignore)]
	public string NotificationText
	{
		get
		{
			short num = 18588;
			short num2 = num;
			num = 18588;
			switch (num2 == num)
			{
			default:
				num = 1;
				if (num != 0)
				{
				}
				num = 0;
				if (num != 0)
				{
				}
				return g;
			}
		}
		set
		{
			short num = 1;
			int num2 = num;
			while (true)
			{
				switch (num2)
				{
				case 1:
					switch (0)
					{
					default:
						goto end_IL_002b;
					case 0:
						break;
					}
					goto default;
				default:
					if (g != value)
					{
						num = 2;
						num2 = num;
						break;
					}
					return;
				case 2:
				{
					num = 1;
					if (num != 0)
					{
					}
					num = 20276;
					short num3 = num;
					num = 20276;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						g = value;
						RaisePropertyChanged("NotificationText");
						num = 0;
						num2 = num;
						break;
					}
					break;
				}
				case 0:
					return;
					end_IL_002b:
					break;
				}
			}
		}
	}

	[JsonProperty("isAutoRepeat", Required = Required.DisallowNull, NullValueHandling = NullValueHandling.Ignore)]
	public bool IsAutoRepeat
	{
		get
		{
			short num = -28759;
			short num2 = num;
			num = -28759;
			switch (num2 == num)
			{
			default:
				num = 0;
				if (num != 0)
				{
				}
				num = 1;
				if (num != 0)
				{
				}
				return h;
			}
		}
		set
		{
			while (true)
			{
				short num = 1;
				int num2 = num;
				while (true)
				{
					switch (num2)
					{
					case 1:
						switch (0)
						{
						default:
							continue;
						case 0:
							break;
						}
						goto default;
					default:
						if (h != value)
						{
							num = 0;
							num2 = num;
							continue;
						}
						goto case 2;
					case 0:
						break;
					case 2:
						num = 1;
						if (num == 0)
						{
						}
						return;
					}
					h = value;
					RaisePropertyChanged("IsAutoRepeat");
					num = -18330;
					short num3 = num;
					num = -18330;
					switch (num3 == num)
					{
					case false:
					case true:
						break;
					default:
						num = 0;
						if (num != 0)
						{
						}
						num = 2;
						num2 = num;
						continue;
					}
					break;
				}
			}
		}
	}

	public event PropertyChangedEventHandler PropertyChanged
	{
		[CompilerGenerated]
		add
		{
			short num = -4696;
			short num2 = num;
			num = -4696;
			switch (num2 == num)
			{
			case false:
			case true:
				return;
			}
			num = 0;
			if (num != 0)
			{
			}
			int num3 = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					switch (num3)
					{
					case 2:
					{
						propertyChangedEventHandler2 = propertyChangedEventHandler;
						PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Combine(propertyChangedEventHandler2, value);
						propertyChangedEventHandler = Interlocked.CompareExchange(ref i, propertyChangedEventHandler3, propertyChangedEventHandler2);
						num = 0;
						num3 = num;
						continue;
					}
					case 0:
						num = 1;
						if (num != 0)
						{
						}
						if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
						{
							num = 1;
							num3 = num;
							continue;
						}
						goto case 2;
					case 1:
						return;
					}
					break;
				}
				goto case 0;
			}
			case 0:
				propertyChangedEventHandler = i;
				num = 2;
				num3 = num;
				goto default;
			}
		}
		[CompilerGenerated]
		remove
		{
			int num = default(int);
			PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
			short num2;
			switch (0)
			{
			default:
			{
				PropertyChangedEventHandler propertyChangedEventHandler2 = default(PropertyChangedEventHandler);
				while (true)
				{
					switch (num)
					{
					case 2:
						goto IL_0045;
					case 1:
						goto IL_00de;
					case 0:
						return;
					}
					break;
					IL_00de:
					num2 = 1;
					if (num2 != 0)
					{
					}
					if ((object)propertyChangedEventHandler == propertyChangedEventHandler2)
					{
						num2 = 0;
						num = num2;
						continue;
					}
					goto IL_00a4;
					IL_0087:
					num2 = 0;
					if (num2 == 0)
					{
					}
					goto IL_00a4;
					IL_00a4:
					propertyChangedEventHandler2 = propertyChangedEventHandler;
					PropertyChangedEventHandler propertyChangedEventHandler3 = (PropertyChangedEventHandler)Delegate.Remove(propertyChangedEventHandler2, value);
					propertyChangedEventHandler = Interlocked.CompareExchange(ref i, propertyChangedEventHandler3, propertyChangedEventHandler2);
					num2 = 1;
					num = num2;
					continue;
					IL_0045:
					num2 = 19053;
					short num3 = num2;
					num2 = 19053;
					switch (num3 == num2)
					{
					case false:
					case true:
						break;
					default:
						goto IL_0087;
					}
					goto IL_0023;
				}
				goto case 0;
			}
			case 0:
				{
					propertyChangedEventHandler = i;
					goto IL_0023;
				}
				IL_0023:
				num2 = 2;
				num = num2;
				goto default;
			}
		}
	}

	protected virtual void RaisePropertyChanged([CallerMemberName] string propertyName = null)
	{
		int num = default(int);
		PropertyChangedEventHandler propertyChangedEventHandler = default(PropertyChangedEventHandler);
		switch (0)
		{
		default:
			while (true)
			{
				switch (num)
				{
				case 2:
					if (propertyChangedEventHandler != null)
					{
						short num2 = 1;
						num = num2;
						continue;
					}
					return;
				case 1:
				{
					propertyChangedEventHandler(this, new PropertyChangedEventArgs(propertyName));
					short num2 = 20059;
					short num3 = num2;
					num2 = 20059;
					switch (num3 == num2)
					{
					case false:
					case true:
						return;
					}
					num2 = 0;
					if (num2 != 0)
					{
					}
					num2 = 0;
					num = num2;
					continue;
				}
				case 0:
					return;
				}
				break;
			}
			goto case 0;
		case 0:
		{
			propertyChangedEventHandler = i;
			short num2 = 1;
			if (num2 != 0)
			{
			}
			num2 = 2;
			num = num2;
			goto default;
		}
		}
	}
}
